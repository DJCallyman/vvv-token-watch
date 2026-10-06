import Link from 'next/link'
import { WifiOff } from 'lucide-react'

export const metadata = {
  title: 'Offline - VVV Token Watch',
}

export default function OfflinePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background p-6 text-center">
      <WifiOff className="h-10 w-10 text-muted-foreground" aria-hidden="true" />
      <h1 className="text-2xl font-bold text-foreground">You are offline</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        VVV Token Watch could not reach the network. Cached pages remain available; live
        data, alerts, and on-chain views will resume when the connection returns.
      </p>
      <Link
        href="/"
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        Retry
      </Link>
    </main>
  )
}
