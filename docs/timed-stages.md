# Timed stages / 2026-10-28

## Requirements

Each Easy puzzle has a 180-second deadline; each Hard puzzle has a 420-second deadline. Show a visible countdown and time-sensitive points. Both deadline and final points belong to the server; clients do not submit elapsed time.

## Start and stop

The first authorized stage access creates one persisted timer keyed by session, mode and stage. Reads of the clue, artifact or timing route cannot reset it. Opening a different mode starts that mode independently. Refreshing, closing the tab or reading hints does not pause. Each next stage starts only when accessed. On the first correct answer received before the deadline, one transaction writes the solve and frozen finish time; duplicate submissions preserve the first points and duration.

Exact deadline equality is expired. Expired stage clue remains readable for learning, but answer/hint/artifact operations reject with 409. The next destination and treasure stay locked. The UI shows 00:00, disabled submission and an explicit retry action.

## Retry policy

A retry is allowed only for an expired, unsolved stage. It starts a new 3/7-minute window with a fresh stage-only seed (including downloadable PNG metadata); the previous flag is invalid. Prior solved stages and mode progress are unchanged. Hint counts persist. Every retry after the first attempt uses 50% of the normal computed points, rounded down; successive retries do not reduce further. Concurrent retry requests create only one new attempt. CSRF, Origin, session authorization, progression and a retry rate cap are enforced.

## Scoring

`B = weight*100`, `T = 180 or 420`, `e = max(0,floor(elapsed_seconds))`, `h = revealed hints`.

`normal = max(0, B/2 + floor(B*(T-e)/(2*T)) - 25*h)` for an answer before the deadline; after it there is no accepted solve. First attempt awards `normal`; later attempts award `floor(normal/2)`.

No client-provided timing/score fields are accepted. The read-side points display is an estimate; network transit may lower the final server award. Maximum five-stage total remains 3000. Leaderboards use the resulting persisted score, then total expedition duration as before.

## Compatibility

Migration adds `stage_timers` without altering existing sessions/solves/hints. Old scores remain immutable; old solves display legacy scoring with no invented elapsed duration. SQLite and backup/rollback preserve the new timing table; reverting application source does not roll back player data or recalculate points.

## Client synchronization

The UI advances elapsed time with performance.now rather than the device wall clock; it syncs every 10 seconds and on focus/visibility return. It subtracts the round-trip duration conservatively. It reloads the clue when another tab starts a new attempt and refreshes session state when another tab solves. Stale generations cannot overwrite a locally started retry or new session. The countdown has role=timer with live announcements off; the timeout transition has a separate status message. A failed sync exposes retry text while the server deadline continues.

## Verification

Deterministic fake server time tests cover both limits, exact deadline boundary, 179.999 seconds, time-decreasing scores, hints, expiry rejection, fresh retry flags, parallel retries/solves, session/mode/stage isolation, reload/restart persistence, extra input fields and legacy migration. Browser tests decode real artifacts, inspect timer movement/freeze, shift only isolated E2E SQLite deadlines (not production), test expiry/retry and confirm mode limits. Existing accessibility, fonts, logos, layouts and complete treasure journey checks remain active.
