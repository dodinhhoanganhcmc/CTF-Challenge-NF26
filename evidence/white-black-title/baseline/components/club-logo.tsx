import Image from 'next/image';

/** Opaque, unaltered artwork: the light/dark variants always keep their own background. */
export default function ClubLogo({ placement = 'header' }: { placement?: 'header' | 'footer' | 'reward' }) {
  const sizes = placement === 'reward' ? '(max-width: 600px) 216px, 248px' : placement === 'footer' ? '112px' : '(max-width: 600px) 68px, 88px';
  return <span className={`club-logo club-logo-${placement}`} data-testid={`club-logo-${placement}`}>
    <Image className="club-logo-light" src="/club-logo-light.jpg?v=20261026" alt="Logo CMC Infrasec" width={1024} height={1024} sizes={sizes} loading={placement === 'header' ? 'eager' : 'lazy'} />
    <Image className="club-logo-dark" src="/club-logo.png?v=20261026" alt="Logo CMC Infrasec" width={1024} height={1024} sizes={sizes} loading={placement === 'header' ? 'eager' : 'lazy'} />
  </span>;
}
