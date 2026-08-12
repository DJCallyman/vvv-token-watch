'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import { ThemeProvider } from '@/components/ThemeProvider'
import { SidebarDrawerProvider } from '@/components/layout/SidebarDrawerContext'
import { Toaster } from 'sonner'

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
          {children}
          <Toaster position="bottom-right" richColors closeButton />
        </SidebarDrawerProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
