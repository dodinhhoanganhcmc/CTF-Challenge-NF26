# Domain
- Expedition: one anonymous session; two independent mode progress records.
- Flag: case-sensitive DAO{...} answer derived for a session, mode and stage.
- Stage: ordinal 1-5; weights 2,4,6,8,10; unlock requires all prior solves.
- Fragment: one per solve; five authorize the treasure.
- Hint: monotonically revealed help; reduces points, not the ability to finish.
- Treasure: final server-authorized result, not a sixth puzzle.

- Organizer: CMC Infrasec; event: NextFest 26.
- Reward: physical club-logo sticker; a stable completion code is issued only after five solves.
- Official logos installed: public/club-logo.png (black primary) and public/club-logo-light.jpg (white alternative). Header/reward use the matching opaque variant for the theme; preserve original artwork, aspect ratio and background. Originals are retained under assets/branding/originals/.
- Leaderboard: public guest name; order by solved count, points, completion duration.

- Typography: Poppins throughout the site, including controls and puzzle payloads; self-hosted Vietnamese subsets.
- Footer: text-only `(c) CMC Infrasec x NextFest '26`; replay is beside the guest summary.

- Stage timing: Easy 180s, Hard 420s, server-owned persisted deadline from first stage access; reload, tab switch, mode switch do not pause/reset.
- Timed scoring: B/2 + floor(B*(T-floor(elapsed))/(2*T)) - hints*25, bounded >=0; after expiry every retry uses a fresh stage-only seed and halves points. No retry before expiry or after solve.
- Deadline equality rejects submission. Solved score/timing are immutable; prior untimed scores stay unchanged and display legacy status instead of fake elapsed values.
