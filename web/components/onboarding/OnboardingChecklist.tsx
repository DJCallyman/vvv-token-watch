'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { CheckCircle2, Circle, X } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const STEPS = [
  {
    id: 'preferences',
    label: 'Review display preferences and the refresh interval',
    href: '/prices',
  },
  {
    id: 'alerts',
    label: 'Create your first alert (threshold, rate of change, or anomaly)',
    href: '/alerts',
  },
  {
    id: 'channels',
    label: 'Add a Discord notification channel and send a test',
    href: '/alerts',
  },
  {
    id: 'wallet',
    label: 'Connect a wallet read-only for on-chain balances',
    href: '/onchain',
  },
] as const

const DISMISS_KEY = 'vvv:onboarding-dismissed'
const PROGRESS_KEY = 'vvv:onboarding-progress'

export function OnboardingChecklist() {
  const [mounted, setMounted] = useState(false)
  const [dismissed, setDismissed] = useState(false)
  const [done, setDone] = useState<string[]>([])

  useEffect(() => {
    setMounted(true)
    try {
      setDismissed(window.localStorage.getItem(DISMISS_KEY) === '1')
      const stored = window.localStorage.getItem(PROGRESS_KEY)
      setDone(stored ? (JSON.parse(stored) as string[]) : [])
    } catch {
      setDone([])
    }
  }, [])

  const toggle = (id: string) => {
    setDone((current) => {
      const next = current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id]
      try {
        window.localStorage.setItem(PROGRESS_KEY, JSON.stringify(next))
      } catch {
        // Storage unavailable; progress is session-only.
      }
      return next
    })
  }

  const dismiss = () => {
    setDismissed(true)
    try {
      window.localStorage.setItem(DISMISS_KEY, '1')
    } catch {
      // Storage unavailable.
    }
  }

  if (!mounted || dismissed) return null
  const completed = STEPS.filter((step) => done.includes(step.id)).length

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3">
        <div>
          <CardTitle>Getting started</CardTitle>
          <CardDescription>
            {completed}/{STEPS.length} complete — first-run guidance for this deployment
          </CardDescription>
        </div>
        <button
          type="button"
          onClick={dismiss}
          aria-label="Dismiss getting started checklist"
          className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {STEPS.map((step) => {
            const isDone = done.includes(step.id)
            return (
              <li key={step.id} className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => toggle(step.id)}
                  aria-pressed={isDone}
                  aria-label={`Mark "${step.label}" as ${isDone ? 'not done' : 'done'}`}
                  className="text-muted-foreground hover:text-foreground"
                >
                  {isDone ? (
                    <CheckCircle2 className="h-5 w-5 text-success" aria-hidden="true" />
                  ) : (
                    <Circle className="h-5 w-5" aria-hidden="true" />
                  )}
                </button>
                <Link
                  href={step.href}
                  className={`text-sm hover:underline ${isDone ? 'text-muted-foreground line-through' : 'text-foreground'}`}
                >
                  {step.label}
                </Link>
              </li>
            )
          })}
        </ul>
      </CardContent>
    </Card>
  )
}
