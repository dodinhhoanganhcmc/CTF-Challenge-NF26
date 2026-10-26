# Security review · CMC Infrasec × NextFest 26

## Trust boundaries

Browser → fixed Next.js allowlist proxy → loopback FastAPI → local SQLite. Client controls its name, chosen mode, tool input and submitted answer; server controls seed, progress, score, hints and completion code. Puzzle artifacts deliberately expose the current unlocked puzzle's answer through its educational solution path.

## Implemented checks

- Random 256-bit guest tokens; only SHA-256 cookie digests stored. HttpOnly, SameSite Strict, 30-day expiry; Secure configurable for HTTPS.
- Exact configured Origin + custom request marker at both proxy and backend; per-session CSRF token required for gameplay writes.
- Streamed body bound of 4096 bytes at both layers; Pydantic length/type/mode checks and control-character rejection for guest names.
- Parameterized SQL; uniqueness constraints and `BEGIN IMMEDIATE` serialize idempotent concurrent solves. Score and treasure gate are server-authoritative.
- Fixed upstream and explicit paths/methods; no user URL fetching, redirects, executable uploads, eval, shell puzzle runners or user HTML rendering.
- Session-specific puzzle flags; no seed/raw future answers in catalog, frontend bundle or error bodies. Wrong flags do not affect score.
- Database-backed attempt limit 40/minute/session, hint limit 30/minute/session, session creation 3000/hour/API peer (shared cap behind local proxy).
- API responses are no-store; downloads are text or PNG with attachment headers. CSP, nosniff, frame denial and same-origin referrers are configured.
- Guest names and clue/code text use React text nodes; local HTML inspection is plain text, not DOM insertion.
- Organizer reward lookup is a local read-only SQLite CLI; no exposed admin credential or remote management endpoint.

## Verification

API tests cover both real puzzle solution paths, cross-session answers, modes, lock bypass attempts, hints, duplicated/concurrent solves, bad names/flags/JSON, streamed body size, CSRF/Origin, expiry, pagination, persistence and reward lookup. Browser tests exercise the same-origin proxy, both full journeys, decoder methods, downloads, replay, responsive layouts, light/dark and axe checks. Dependency audit JSON lives in `evidence/`.

## Operating facts

This event uses display names, not verified identities. Multiple expeditions can share a name; the board does not establish who owns a real-world identity. The completion code proves a recorded expedition finished, not that a person has already received a sticker. Staff perform in-person handout and reconciliation. Database access is local to the host. No arbitrary challenge service is intentionally vulnerable.

Production uses HTTPS and COOKIE_SECURE=1, the real APP_ORIGINS on both services, one API process and persistent SQLite. Current CSP permits inline Next.js bootstrap scripts but denies foreign origins, embedding, plugins and foreign form targets. The included launcher is local-only and does not configure hosting or third-party services.
