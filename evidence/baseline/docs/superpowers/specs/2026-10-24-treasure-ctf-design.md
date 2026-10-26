# Treasure CTF design

Approved direction: friendly adventure, Vietnamese, five stages, Easy/Hard. Local Markdown issues and default triage vocabulary approved.

## Architecture
Browser -> Next.js App Router -> allowlisted same-origin API proxy -> FastAPI -> SQLite. Public catalog contains descriptions, never raw answers. Per-session flags are derived server-side; public puzzle artifacts intentionally encode only unlocked-stage flags. Anonymous opaque HttpOnly cookie is stored as a SHA-256 hash in SQLite. CSRF token is session-bound and required for writes after session creation. Same-origin creation requires a custom header and validates Origin.

## Gameplay
Stages and weights: message in a bottle/Base64 (2), rotating compass/Caesar (4), old observatory/HTML inspection (6), lighthouse archive/log reconstruction or PNG metadata (8), vault/XOR (10). Easy teaches the method and supplies a local decoder with sample data. Hard changes payloads, combines transformations, and gives fewer contextual hints. Flag prefix is DAO; matching trims outer whitespace but is otherwise case-sensitive. Three hints per stage reduce earned points, never progression. Each solve unlocks the next stage, adds one compass fragment, and records a debrief. Duplicate solves are idempotent. Separate progress for both modes. Five solves authorize a final treasure read; replay creates a new session without deleting the old one.

## UI
Map-led first viewport, large title, orange action accent, pale ocean canvas, dark forest ink, crisp geometric island silhouettes, illustrated destinations using consistent Phosphor icons. One current mission panel. Accessible location list is the mobile route, no tiny desktop map squeezed onto a phone. Journal, beginner guide, decoding bench, and completion screen are real surfaces. Inline errors, retry, empty/loading/solved/locked states.

## Data and errors
SQLite stores session hashes, expiration, mode, solves, attempts, hints and points. Parameterized SQL and transactions enforce state. Invalid JSON/type/flag lengths produce RFC 7807 problem responses. Missing session 401, invalid CSRF/origin 403, unknown stage 404, locked stage/treasure 409, excessive requests 429, oversized body 413. No code execution, shell access, remote fetching or user HTML rendering in puzzles.

## Tests
Run both modes through all five real solution paths, flag rejection, cross-session answers, sequential unlock, treasure gate, duplicated/concurrent solves, hint scoring, isolation, CSRF, Origin, validation, body limits, rate limits and restart persistence. Typecheck, production build, dependency audit, OpenAPI lint. Browser E2E checks the complete treasure journey, all controls, light/dark and widths 320/375/414/768/1440. One batched visual inspection plus one confirmation pass.

## Implementation plan
1. Backend puzzles, persistence, API schemas and controls; test independently.
2. Map-led Next.js UI and tool bench; typecheck/build.
3. Full journey E2E and responsive/accessibility checks.
4. Security reports, startup instructions, original hash/diff/rollback verification.

## Self-review
No undecided functional requirements. Deployment assumptions documented; no multi-tenant accounts, leaderboard or paid AI model added. Puzzle scope deliberately beginner-level.
