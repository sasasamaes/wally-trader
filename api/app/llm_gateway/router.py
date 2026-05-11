"""Provider-agnostic LLM Gateway.

The single public surface for agent code. Hides:
- Provider key lookup + decryption
- SDK instantiation
- Stream normalization
- Token + cost accounting → DB

Usage from an agent:

    gateway = LLMGateway(db_session, settings)
    async for chunk in gateway.stream(
        user_id=user.id,
        provider="anthropic",
        request=ChatRequest(
            messages=[Message(role=Role.user, content="hi")],
            model="claude-sonnet-4-6",
        ),
        agent_name="regime",
    ):
        if chunk.type == "text":
            ...
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.logging import log
from app.llm_gateway.anthropic_client import AnthropicClient
from app.llm_gateway.base_client import LLMClient
from app.llm_gateway.google_client import GoogleClient
from app.llm_gateway.ollama_client import OllamaClient
from app.llm_gateway.openai_client import OpenAIClient
from app.llm_gateway.schemas import ChatRequest, StreamChunk
from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.api_key import ApiKeyLLM, LLMProvider
from app.models.usage_event import UsageEvent
from app.security.encryption import decrypt_secret


class MissingApiKeyError(Exception):
    """User hasn't added a key for this provider."""


class LLMGateway:
    """Routes a chat request to the right provider client."""

    def __init__(self, db: AsyncSession, settings: Settings) -> None:
        self._db = db
        self._settings = settings

    async def _get_user_key(
        self, user_id: uuid.UUID, provider: LLMProvider
    ) -> str:
        stmt = select(ApiKeyLLM).where(
            ApiKeyLLM.user_id == user_id, ApiKeyLLM.provider == provider
        )
        row = (await self._db.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise MissingApiKeyError(
                f"No API key set for provider '{provider.value}'. "
                f"Add one under Settings → Keys."
            )
        plaintext = decrypt_secret(
            row.encrypted_key,
            row.encrypted_dek,
            row.nonce,
            row.salt,
            self._settings.MASTER_KEK.get_secret_value(),
        )
        # Touch last_used asynchronously; safe to fail silently — it's metadata.
        row.last_used = datetime.utcnow()
        return plaintext

    def _client_for(self, provider: LLMProvider, key: str) -> LLMClient:
        if provider is LLMProvider.anthropic:
            return AnthropicClient(key)
        if provider is LLMProvider.openai:
            return OpenAIClient(key)
        if provider is LLMProvider.google:
            return GoogleClient(key)
        if provider is LLMProvider.ollama:
            return OllamaClient(key)
        raise ValueError(f"Unknown provider: {provider}")

    async def stream(
        self,
        *,
        user_id: uuid.UUID,
        provider: LLMProvider,
        request: ChatRequest,
        agent_name: str,
        agent_run_id: uuid.UUID | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream a chat completion and record usage to the DB.

        Caller can pass an existing `agent_run_id` if the agent has already
        opened an AgentRun row; otherwise we don't record (the agent layer
        always opens one, so this is mostly a safety net for direct callers).
        """
        try:
            key = await self._get_user_key(user_id, provider)
        except MissingApiKeyError as exc:
            yield StreamChunk(type="error", error=str(exc))
            yield StreamChunk(type="done")
            return

        client = self._client_for(provider, key)
        accumulated_text: list[str] = []
        usage = None

        async for chunk in client.stream(request):
            if chunk.type == "text" and chunk.delta is not None:
                accumulated_text.append(chunk.delta)
            elif chunk.type == "usage":
                usage = chunk.usage
            yield chunk

        if usage and agent_run_id is not None:
            await self._record_usage(
                user_id=user_id,
                run_id=agent_run_id,
                provider=provider,
                model=request.model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                cost_usd=usage.cost_usd,
                output_md="".join(accumulated_text),
            )

    async def _record_usage(
        self,
        *,
        user_id: uuid.UUID,
        run_id: uuid.UUID,
        provider: LLMProvider,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        output_md: str,
    ) -> None:
        # Update AgentRun row
        run = await self._db.get(AgentRun, run_id)
        if run is not None:
            run.llm_provider = provider
            run.model = model
            run.prompt_tokens = prompt_tokens
            run.completion_tokens = completion_tokens
            run.cost_usd = Decimal(str(round(cost_usd, 6)))
            run.output_md = output_md
            run.status = AgentRunStatus.completed

        # Insert UsageEvent (token cost only; per-agent flat fee added by
        # the billing layer at flush time).
        unit = Decimal(str(round(cost_usd, 6))) if cost_usd > 0 else Decimal("0")
        event = UsageEvent(
            user_id=user_id,
            run_id=run_id,
            event_type="llm_tokens",
            quantity=float(prompt_tokens + completion_tokens),
            unit_cost_usd=unit,
            total_cost_usd=unit,
        )
        self._db.add(event)
        await self._db.flush()
        log.info(
            "llm.usage.recorded",
            run_id=str(run_id),
            provider=provider.value,
            model=model,
            tokens=prompt_tokens + completion_tokens,
            cost_usd=cost_usd,
        )
