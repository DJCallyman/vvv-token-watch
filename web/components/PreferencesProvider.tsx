'use client'

import { createContext, useContext } from 'react'
import { usePathname } from 'next/navigation'
import { useSettings } from '@/lib/hooks'
import type { DisplayCurrency } from '@/lib/api'

interface DisplayPreferences {
  currency: DisplayCurrency
  timezone: string
}

const DEFAULT_DISPLAY_PREFERENCES: DisplayPreferences = {
  currency: 'USD',
  timezone: 'local',
}

const DisplayPreferencesContext = createContext(DEFAULT_DISPLAY_PREFERENCES)

export function PreferencesProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { data: settings } = useSettings(pathname !== '/login')
  const value = settings
    ? { currency: settings.display_currency, timezone: settings.timezone }
    : DEFAULT_DISPLAY_PREFERENCES

  return (
    <DisplayPreferencesContext.Provider value={value}>
      {children}
    </DisplayPreferencesContext.Provider>
  )
}

export function useDisplayPreferences() {
  return useContext(DisplayPreferencesContext)
}
