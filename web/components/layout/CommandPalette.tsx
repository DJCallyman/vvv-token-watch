'use client'

import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { useQueryClient } from '@tanstack/react-query'
import { Moon, RefreshCw, Sun } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { toast } from 'sonner'
import { useTheme } from '@/components/ThemeProvider'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { navigationItems } from './Sidebar'

interface PaletteCommand {
  id: string
  label: string
  keywords: string
  icon: LucideIcon
  run: () => void | Promise<void>
}

const OPEN_EVENT = 'vvv:open-command-palette'

export function CommandPalette() {
  const pathname = usePathname()
  const router = useRouter()
  const queryClient = useQueryClient()
  const { theme, toggleTheme } = useTheme()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const inputId = useId()
  const listId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const optionRefs = useRef<Record<string, HTMLButtonElement | null>>({})

  useEffect(() => {
    const openPalette = () => setOpen(true)
    const handleShortcut = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setOpen(true)
      }
    }
    window.addEventListener(OPEN_EVENT, openPalette)
    window.addEventListener('keydown', handleShortcut)
    return () => {
      window.removeEventListener(OPEN_EVENT, openPalette)
      window.removeEventListener('keydown', handleShortcut)
    }
  }, [])

  useEffect(() => {
    if (pathname === '/login') setOpen(false)
  }, [pathname])

  const commands = useMemo<PaletteCommand[]>(() => [
      ...navigationItems.map((item) => ({
        id: `route:${item.href}`,
        label: item.name,
        keywords: `navigate page ${item.name}`,
        icon: item.icon,
        run: () => {
          setOpen(false)
          setQuery('')
          router.push(item.href)
        },
      })),
      {
        id: 'action:refresh',
        label: 'Refresh data',
        keywords: 'reload refresh queries data',
        icon: RefreshCw,
        run: async () => {
          setOpen(false)
          try {
            await queryClient.invalidateQueries({}, { throwOnError: true })
            toast.success('Data refreshed')
          } catch (error) {
            toast.error(error instanceof Error ? error.message : 'Failed to refresh data')
          }
        },
      },
      {
        id: 'action:theme',
        label: `Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`,
        keywords: 'theme appearance dark light',
        icon: theme === 'dark' ? Sun : Moon,
        run: () => {
          toggleTheme()
          setOpen(false)
        },
      },
    ], [queryClient, router, theme, toggleTheme])

  const filteredCommands = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()
    if (!normalizedQuery) return commands
    return commands.filter((command) =>
      `${command.label} ${command.keywords}`.toLowerCase().includes(normalizedQuery),
    )
  }, [commands, query])

  useEffect(() => {
    const command = filteredCommands[activeIndex]
    if (open && command) optionRefs.current[command.id]?.scrollIntoView?.({ block: 'nearest' })
  }, [activeIndex, filteredCommands, open])

  const selectActiveCommand = () => {
    const command = filteredCommands[activeIndex]
    if (command) void command.run()
  }

  if (pathname === '/login') return null

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen)
        if (!nextOpen) {
          setQuery('')
          setActiveIndex(0)
        }
      }}
    >
      <DialogContent
        aria-labelledby={`${inputId}-title`}
        className="max-w-xl gap-0 overflow-hidden p-0"
        onOpenAutoFocus={(event) => {
          event.preventDefault()
          inputRef.current?.focus()
        }}
      >
        <div className="border-b border-border p-4">
          <DialogTitle id={`${inputId}-title`} className="sr-only">Command palette</DialogTitle>
          <Input
            ref={inputRef}
            id={inputId}
            aria-label="Search pages and actions"
            aria-controls={listId}
            aria-activedescendant={filteredCommands[activeIndex] ? `${listId}-${filteredCommands[activeIndex].id}` : undefined}
            value={query}
            onChange={(event) => {
              setQuery(event.target.value)
              setActiveIndex(0)
            }}
            onKeyDown={(event) => {
              if (!filteredCommands.length) return
              if (event.key === 'ArrowDown') {
                event.preventDefault()
                setActiveIndex((index) => (index + 1) % filteredCommands.length)
              } else if (event.key === 'ArrowUp') {
                event.preventDefault()
                setActiveIndex((index) => (index - 1 + filteredCommands.length) % filteredCommands.length)
              } else if (event.key === 'Enter') {
                event.preventDefault()
                selectActiveCommand()
              }
            }}
            placeholder="Search pages and actions"
            className="border-0 shadow-none focus-visible:ring-0"
          />
        </div>
        <div id={listId} role="listbox" aria-label="Pages and actions" className="max-h-[min(60vh,24rem)] overflow-y-auto p-2">
          {filteredCommands.length ? filteredCommands.map((command, index) => {
            const Icon = command.icon
            return (
              <button
                key={command.id}
                ref={(element) => { optionRefs.current[command.id] = element }}
                id={`${listId}-${command.id}`}
                type="button"
                role="option"
                aria-selected={activeIndex === index}
                onMouseMove={() => setActiveIndex(index)}
                onClick={() => void command.run()}
                className={`flex min-h-11 w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${activeIndex === index ? 'bg-accent text-accent-foreground' : 'text-foreground hover:bg-accent/60'}`}
              >
                <Icon className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                <span className="truncate">{command.label}</span>
              </button>
            )
          }) : (
            <p className="px-3 py-6 text-center text-sm text-muted-foreground">No matching commands.</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}