'use client'

import { createContext, useContext, useState } from 'react'

interface SidebarDrawerContextValue {
  open: boolean
  setOpen: (open: boolean) => void
  toggle: () => void
}

const SidebarDrawerContext = createContext<SidebarDrawerContextValue>({
  open: false,
  setOpen: () => undefined,
  toggle: () => undefined,
})

export function SidebarDrawerProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <SidebarDrawerContext.Provider value={{ open, setOpen, toggle: () => setOpen((value) => !value) }}>
      {children}
    </SidebarDrawerContext.Provider>
  )
}

export function useSidebarDrawer() {
  return useContext(SidebarDrawerContext)
}
