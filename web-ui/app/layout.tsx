import type { Metadata } from 'next';
import { Inter, Space_Grotesk } from 'next/font/google';
import './globals.css';
import AppShell from '@/components/AppShell';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });
const space = Space_Grotesk({ subsets: ['latin'], variable: '--font-space' });

export const metadata: Metadata = {
  title: 'Agentic Honeypot Dashboard',
  description: 'AI Defense System Command Center',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${space.variable} font-sans`}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
