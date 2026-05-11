# Provisioning checklist

Steps to bring the beta environment online once code is ready to deploy.
Each requires a one-time manual sign-up — Wally Trader doesn't have the
permissions to do them programmatically.

## 1. Clerk (auth)

1. Sign up at https://clerk.com (free up to 10k MAU).
2. Create application "Wally Trader".
3. Enable email/password + Google OAuth.
4. Copy from "API Keys":
   - `CLERK_PUBLISHABLE_KEY` → web `.env.local` + Vercel env var (NEXT_PUBLIC_…)
   - `CLERK_SECRET_KEY` → api `.env` + Fly secret
   - `CLERK_JWT_ISSUER` (Frontend API URL) → api `.env`
5. Configure webhook endpoint:
   - URL: `https://api.wallytrader.com/api/v1/auth/webhook`
   - Events: `user.created`, `user.updated`, `user.deleted`
   - Copy signing secret → `CLERK_WEBHOOK_SECRET`

## 2. Stripe (billing)

1. Sign up at https://stripe.com. Keep in **test mode** for beta.
2. Create product "Wally Beta" with $9/month recurring price.
   - Copy price ID → `STRIPE_PRICE_ID_BASE`
3. Create meter "agent_calls" (Usage > Meters):
   - Event name: `agent_call`
   - Aggregation: `sum`
   - Customer mapping: `payload.stripe_customer_id`
   - Copy meter ID → `STRIPE_METER_AGENT_CALLS_ID`
4. Get API keys (Developers > API keys):
   - Publishable key → web env (NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY)
   - Secret key → `STRIPE_SECRET_KEY`
5. Configure webhook endpoint:
   - URL: `https://api.wallytrader.com/api/v1/billing/webhook`
   - Events: `customer.subscription.*`, `invoice.payment_succeeded`,
     `invoice.payment_failed`, `customer.updated`
   - Copy signing secret → `STRIPE_WEBHOOK_SECRET`

## 3. Fly.io (backend hosting)

1. Sign up at https://fly.io. Add a payment method (required even for
   small machines — they charge by use).
2. Install `flyctl`: `brew install flyctl`
3. From `infra/`, run:
   ```bash
   fly launch --no-deploy --copy-config --name wally-api
   fly pg create --name wally-pg --region iad
   fly pg attach wally-pg --app wally-api          # sets DATABASE_URL
   fly redis create --name wally-redis --region iad
   # Copy the Redis URL into secrets:
   fly secrets set REDIS_URL=redis://default:…@…upstash.io:6379
   ```
4. Set the rest of the secrets:
   ```bash
   fly secrets set \
     MASTER_KEK=$(python -c "from app.security.encryption import generate_master_kek; print(generate_master_kek())") \
     CLERK_SECRET_KEY=… \
     CLERK_WEBHOOK_SECRET=… \
     CLERK_JWT_ISSUER=… \
     STRIPE_SECRET_KEY=… \
     STRIPE_WEBHOOK_SECRET=… \
     STRIPE_PRICE_ID_BASE=… \
     STRIPE_METER_AGENT_CALLS_ID=…
   ```
5. **Back up the MASTER_KEK to 1Password admin vault.** Loss = irrecoverable user data.
6. Deploy: `fly deploy --config infra/fly.toml`

## 4. Vercel (frontend hosting)

1. Sign up at https://vercel.com (free Hobby tier).
2. Connect GitHub repo. Set project root to `web/`.
3. Add environment variables in the Vercel dashboard (Production scope):
   - `NEXT_PUBLIC_API_URL=https://api.wallytrader.com`
   - `NEXT_PUBLIC_APP_URL=https://app.wallytrader.com`
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=…`
   - `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=…`
   - `CLERK_SECRET_KEY=…` (required by `@clerk/nextjs` server actions)
4. Configure custom domain `app.wallytrader.com`.

## 5. Domain (DNS)

1. Buy `wallytrader.com` (Namecheap, Porkbun, etc.) — ~$15/year.
2. Configure DNS:
   - `app.wallytrader.com` → CNAME to Vercel
   - `api.wallytrader.com` → CNAME / A record to Fly (run `fly certs add`)
   - `wallytrader.com` (apex) → optional marketing site

## 6. Sentry (optional, observability)

1. Sign up at https://sentry.io (5k events/month free).
2. Create project "wally-api" (Python/FastAPI) and "wally-web" (Next.js).
3. Copy DSN values into `SENTRY_DSN` env var on each service.
