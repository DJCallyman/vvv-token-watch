'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { ThemeProvider } from '@/components/ThemeProvider'
import { SidebarDrawerProvider } from '@/components/layout/SidebarDrawerContext'
import { Toaster } from 'sonner'
import { CommandPalette } from '@/components/layout/CommandPalette'
import { PreferencesProvider } from '@/components/PreferencesProvider'
import { OfflineBanner } from '@/components/layout/OfflineBanner'
import { HelpDialog } from '@/components/help/HelpDialog'
import { ServiceWorkerRegistrar } from '@/components/ServiceWorkerRegistrar'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
          },
        },
      })
  )

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <SidebarDrawerProvider>
          <PreferencesProvider>
            <OfflineBanner />
            {children}
            <Toaster position="bottom-right" richColors closeButton />
            <CommandPalette />
            <HelpDialog />
            <ServiceWorkerRegistrar />
          </PreferencesProvider>
        </SidebarDrawerProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
