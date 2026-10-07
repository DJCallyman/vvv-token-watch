import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from './providers'
import { SkipLink } from '@/components/layout/SkipLink'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'VVV Token Watch',
  description: 'Monitor Venice AI API usage, balances, and token prices',
  manifest: '/manifest.webmanifest',
  appleWebApp: {
    capable: true,
    title: 'VVV Watch',
    statusBarStyle: 'black-translucent',
  },
  icons: {
    icon: [
      { url: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      { url: '/icon-512.png', sizes: '512x512', type: 'image/png' },
    ],
    apple: [{ url: '/icon-192.png', sizes: '192x192', type: 'image/png' }],
  },
}

export const viewport: Viewport = {
  themeColor: '#0f172a',
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          <SkipLink />
          {children}
        </Providers>
      </body>
    </html>
  )
}
