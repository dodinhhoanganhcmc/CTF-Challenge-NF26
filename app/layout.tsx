import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Đảo Mật Mã · CMC Infrasec × NextFest 26',
  description: 'Chuyến săn kho báu CTF 5 màn dành cho người mới. Giải mật mã, ghép la bàn, nhận sticker CMC Infrasec tại NextFest 26.',
  robots: { index: false, follow: false },
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="vi"><body>{children}</body></html>;
}
