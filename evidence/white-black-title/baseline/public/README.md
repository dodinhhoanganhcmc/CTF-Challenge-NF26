# CMC Infrasec official artwork

- `/club-logo.png`: black background, white artwork; primary supplied PNG normalized to 1024×1024.
- `/club-logo-light.jpg`: white background, black artwork; exact supplied alternative JPEG.

The `ClubLogo` component uses the light alternative in the light theme and the primary in the dark theme at the header, footer and authorized treasure screen. Both remain opaque: no crop, inversion, recoloring, background removal or circular mask. The originals remain byte-for-byte under `assets/branding/originals/`.

Rebuild and restart Next.js after changing public assets.
