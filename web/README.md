# web/ — Wally Trader Frontend

Next.js 15 + React 19 + TypeScript + Tailwind + shadcn/ui.

This is the customer-facing web app. See `../docs/superpowers/plans/2026-05-11-web-app-bootstrap.md`
for full architecture context.

## Quick start

```bash
cd web
npm install
cp .env.local.example .env.local   # fill in NEXT_PUBLIC_API_URL + Clerk keys
npm run dev                         # http://localhost:3000
```

## Layout (App Router)

```
app/
├── (marketing)/        # public landing + waitlist
├── (auth)/             # Clerk-managed sign-in / sign-up
├── (app)/              # authenticated app shell
│   ├── dashboard/
│   ├── profiles/[slug]/
│   ├── agents/         # streaming chat UI
│   ├── signals/        # signals log + filters
│   ├── settings/
│   │   ├── keys/       # LLM + broker BYOK
│   │   └── billing/    # Stripe portal embed
│   └── onboarding/     # first-run wizard
└── api/                # Next.js route handlers (light glue only)
```

## Stack

- **next@^15** App Router, RSC
- **react@^19**, **typescript@^5**
- **tailwindcss@^4** + **shadcn/ui** components
- **@clerk/nextjs** auth
- **lightweight-charts@^5** for equity / price charts
- **@tanstack/react-query** server state
- **@tanstack/react-table** signals log
- **zod** schemas shared with backend Pydantic models
- **stripe** client-side checkout redirect
