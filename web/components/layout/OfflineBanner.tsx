'use client'

import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { WifiOff } from 'lucide-react'

/** Offline status banner with a retry action (Phase 4). */
export function OfflineBanner() {
  const queryClient = useQueryClient()
  const [offline, setOffline] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const update = () => setOffline(!window.navigator.onLine)
    update()
    window.addEventListener('online', update)
    window.addEventListener('offline', update)
    return () => {
      window.removeEventListener('online', update)
      window.removeEventListener('offline', update)
    }
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const onOnline = () => {
      void queryClient.invalidateQueries()
    }
    window.addEventListener('online', onOnline)
    return () => window.removeEventListener('online', onOnline)
  }, [queryClient])

  if (!offline) return null

  return (
    <div
      role="status"
      className="fixed inset-x-0 top-0 z-[60] flex flex-wrap items-center justify-center gap-3 bg-amber-500/95 px-4 py-2 text-sm text-black"
    >
      <WifiOff className="h-4 w-4" aria-hidden="true" />
      <span>You are offline — showing the last known data.</span>
      <button
        type="button"
        onClick={() => { void queryClient.invalidateQueries() }}
        className="rounded border border-black/30 px-2 py-0.5 text-xs font-medium hover:bg-black/10"
      >
        Retry now
      </button>
    </div>
  )
}
