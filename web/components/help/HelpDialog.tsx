'use client'

import { useEffect, useState } from 'react'
import { Keyboard, HelpCircle } from 'lucide-react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'

export const HELP_EVENT = 'vvv:open-help'

export const SHORTCUTS: Array<{ keys: string; description: string }> = [
  { keys: 'Ctrl/⌘ + K', description: 'Open the command palette' },
  { keys: '?', description: 'Open this help panel' },
  { keys: 'Esc', description: 'Close the active dialog or palette' },
  { keys: 'Tab', description: 'Move focus through controls; every action is keyboard reachable' },
  { keys: 'Ctrl/⌘ + R', description: 'Refresh all data (command palette also offers this)' },
]

export const GLOSSARY: Array<{ term: string; definition: string }> = [
  { term: 'VVV', definition: 'Venice governance token; staking VVV produces sVVV and DIEM.' },
  { term: 'DIEM', definition: 'Daily inference credit minted by staked VVV; consumed as inference capacity when staked.' },
  { term: 'sVVV', definition: 'Staked VVV position, including locked (cooldown-committed) and unlocked portions.' },
  { term: 'Free float', definition: 'The share of supply actually tradable right now: circulating supply minus staked, vesting, and burned amounts.' },
  { term: 'Epoch', definition: 'Venice billing window (24 hours by default) that resets daily usage limits.' },
  { term: 'FDV', definition: 'Fully diluted valuation: price multiplied by total supply.' },
  { term: 'Rate of change', definition: 'Percent change between the latest value and the value at least one configured window earlier.' },
  { term: 'Anomaly z-score', definition: 'How many population standard deviations the latest value sits from the mean of earlier samples.' },
  { term: 'RPC credits', definition: 'Venice Crypto RPC usage units reported per response in X-Venice-RPC-Credits headers.' },
]

/** Glossary tooltip term: dotted underline plus native tooltip. */
export function GlossaryTerm({ term, children }: { term: string; children?: React.ReactNode }) {
  const entry = GLOSSARY.find((item) => item.term.toLowerCase() === term.toLowerCase())
  return (
    <abbr
      title={entry?.definition ?? term}
      className="cursor-help underline decoration-dotted underline-offset-2"
    >
      {children ?? term}
    </abbr>
  )
}

export function HelpDialog() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const openHelp = () => setOpen(true)
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== '?' || event.metaKey || event.ctrlKey || event.altKey) return
      const target = event.target as HTMLElement | null
      const tag = target?.tagName?.toLowerCase()
      if (tag === 'input' || tag === 'textarea' || tag === 'select' || target?.isContentEditable) return
      event.preventDefault()
      setOpen(true)
    }
    window.addEventListener(HELP_EVENT, openHelp)
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener(HELP_EVENT, openHelp)
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [])

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <HelpCircle className="h-5 w-5" aria-hidden="true" />
            Keyboard shortcuts &amp; glossary
          </DialogTitle>
          <DialogDescription>
            Contextual help for VVV Token Watch. Press ? anywhere to reopen this panel.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-6 sm:grid-cols-2">
          <section>
            <h2 className="flex items-center gap-2 text-sm font-semibold">
              <Keyboard className="h-4 w-4" aria-hidden="true" />
              Shortcuts
            </h2>
            <dl className="mt-2 space-y-2">
              {SHORTCUTS.map((shortcut) => (
                <div key={shortcut.keys} className="flex items-start justify-between gap-3 text-sm">
                  <dt className="rounded border border-border bg-muted px-2 py-0.5 font-mono text-xs">
                    {shortcut.keys}
                  </dt>
                  <dd className="text-right text-muted-foreground">{shortcut.description}</dd>
                </div>
              ))}
            </dl>
          </section>
          <section>
            <h2 className="text-sm font-semibold">Glossary</h2>
            <dl className="mt-2 space-y-2">
              {GLOSSARY.map((entry) => (
                <div key={entry.term} className="text-sm">
                  <dt className="font-medium">{entry.term}</dt>
                  <dd className="text-muted-foreground">{entry.definition}</dd>
                </div>
              ))}
            </dl>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  )
}
