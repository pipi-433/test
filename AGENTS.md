# AGENTS.md

## Workspace Scope

Work only inside `D:\py\dota` unless the user explicitly authorizes an outside path with `ALLOW_OUTSIDE_WORKSPACE`.

Do not modify files inside `示范景区公开资料包/`. Treat them as read-only source materials.

## Project Context

This project is for 中国软件杯 A5: 景区导览服务 AI 数字人.

Always read these first:

- `SOFTBEI_A5_PLAN.md`
- `SOFTBEI_A5_PRD.md`

The product is `灵境导游`: a scenic-area AI digital human guide covering:

- Mobile App/PWA visitor side
- Scenic-area Kiosk terminal
- Admin dashboard
- Local knowledge base and RAG
- Multimodal image recognition
- Digital human voice, expression, and lip-sync
- Route recommendation
- Visitor feedback and analytics

## Current Execution Priority

Follow the PRD task order.

Start with:

1. Task 01: project initialization
2. Task 01.5: design system and three frontend shells
3. Task 02: data parsing
4. Task 03: database and API
5. Task 04: RAG Q&A
6. Task 04.5: multimodal minimum loop

Do not jump to later flashy features before the earlier tasks work.

## UI/UX Rules

All frontend display pages must follow `ui-ux-pro-max` principles and the PRD design system.

Required routes:

- `/` mobile App/PWA visitor UI
- `/kiosk` scenic-area terminal UI
- `/admin` admin dashboard

Design tone:

- quiet
- trustworthy
- cultural
- tool-like
- not a marketing landing page

Use:

- turquoise / lake green as primary
- bronze / Buddhist gold as accent
- white, light gray, ink text as neutrals
- unified SVG or lucide icons

Avoid:

- emoji as structural icons
- card-inside-card layouts
- one-color themes
- decorative gradient blobs
- tiny touch targets
- hover-only interactions

Touch targets:

- mobile: at least 44px
- kiosk: at least 64px

## API Key and Provider Rules

Never put real API keys in frontend code, README, examples, or committed files.

Use `.env.example` with empty placeholders only.

Default mode must work without API keys using mock providers.

Provider abstraction is required for:

- LLM
- Embedding
- VLM
- TTS

Frontend must call the backend only. It must not call model vendors directly.

## Engineering Rules

Prefer small, verifiable vertical slices.

Every task should leave the app runnable.

Add mock data/provider behavior before real provider integrations.

For errors, use a consistent shape:

```json
{
  "code": "ERROR_CODE",
  "message": "User-facing message",
  "cause": "Developer-facing cause",
  "fix": "How to fix it"
}
```

## Testing and Verification

When changing code, run the relevant checks if available.

At minimum verify:

- backend health endpoint
- frontend routes `/`, `/kiosk`, `/admin`
- no obvious console/runtime errors
- mock mode works without API keys

Future required evals:

- `evals/qa_lingshan.jsonl`
- `evals/vision_samples.jsonl`
- `evals/reports/qa_latest.json`
- `evals/reports/vision_latest.json`

## Non-Goals

Do not implement in early tasks:

- real payment
- ticketing
- order system
- real GPS navigation
- native iOS/Android app
- production 3D digital human
- full multi-tenant SaaS
- self-trained foundation model

## Delivery Style

After each task, report:

- files changed
- how to run
- what was verified
- what remains
