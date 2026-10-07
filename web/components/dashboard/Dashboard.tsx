'use client'

import { useEffect, useState } from 'react'
import { ChevronDown, ChevronUp, GripVertical, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui'
import { useSettings, useUpdateSettings } from '@/lib/hooks'
import type { DashboardWidget } from '@/lib/api'
import { HeroBalanceCard } from './HeroBalanceCard'
import { TodayUsageCard } from './TodayUsageCard'
import { PriceCards } from './PriceCards'
import { UsageLeaderboardCard } from './UsageLeaderboardCard'
import { OnboardingChecklist } from '@/components/onboarding/OnboardingChecklist'

const DEFAULT_LAYOUT: DashboardWidget[] = [
  'balance',
  'usage',
  'prices',
  'usage_leaderboard',
]

const WIDGET_LABELS: Record<DashboardWidget, string> = {
  balance: 'Account balance',
  usage: 'Epoch usage',
  prices: 'Token prices',
  usage_leaderboard: 'API key usage',
}

function isDashboardLayout(value: unknown): value is DashboardWidget[] {
  return Array.isArray(value)
    && value.length === DEFAULT_LAYOUT.length
    && new Set(value).size === DEFAULT_LAYOUT.length
    && DEFAULT_LAYOUT.every((widget) => value.includes(widget))
}

export function Dashboard() {
  const { data: settings, isLoading: settingsLoading } = useSettings()
  const updateSettings = useUpdateSettings()
  const [layout, setLayout] = useState<DashboardWidget[]>(DEFAULT_LAYOUT)
  const [draggedWidget, setDraggedWidget] = useState<DashboardWidget | null>(null)

  useEffect(() => {
    if (settings && isDashboardLayout(settings.dashboard_layout)) {
      setLayout(settings.dashboard_layout)
    }
  }, [settings])

  const saveLayout = async (nextLayout: DashboardWidget[]) => {
    const previousLayout = layout
    setLayout(nextLayout)
    try {
      await updateSettings.mutateAsync({ dashboard_layout: nextLayout })
    } catch {
      setLayout(previousLayout)
    }
  }

  const moveWidget = (widget: DashboardWidget, direction: -1 | 1) => {
    const currentIndex = layout.indexOf(widget)
    const nextIndex = currentIndex + direction
    if (nextIndex < 0 || nextIndex >= layout.length) return
    const nextLayout = [...layout]
    ;[nextLayout[currentIndex], nextLayout[nextIndex]] = [
      nextLayout[nextIndex],
      nextLayout[currentIndex],
    ]
    void saveLayout(nextLayout)
  }

  const dropWidget = (target: DashboardWidget) => {
    if (!draggedWidget || draggedWidget === target) return
    const nextLayout = layout.filter((widget) => widget !== draggedWidget)
    const targetIndex = nextLayout.indexOf(target)
    nextLayout.splice(targetIndex, 0, draggedWidget)
    setDraggedWidget(null)
    void saveLayout(nextLayout)
  }

  const renderWidget = (widget: DashboardWidget) => {
    switch (widget) {
      case 'balance':
        return <HeroBalanceCard />
      case 'usage':
        return <TodayUsageCard />
      case 'prices':
        return <PriceCards />
      case 'usage_leaderboard':
        return <UsageLeaderboardCard />
    }
  }

  const controlsDisabled = settingsLoading || updateSettings.isPending

  return (
    <section aria-label="Dashboard" className="space-y-4">
      <OnboardingChecklist />
      <div className="flex justify-end">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={controlsDisabled || layout.every((widget, index) => widget === DEFAULT_LAYOUT[index])}
          onClick={() => { void saveLayout(DEFAULT_LAYOUT) }}
        >
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
          Reset layout
        </Button>
      </div>
      <div role="list" aria-label="Dashboard widgets" className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {layout.map((widget, index) => (
          <div
            key={widget}
            role="listitem"
            data-widget-id={widget}
            draggable={!controlsDisabled}
            onDragStart={() => setDraggedWidget(widget)}
            onDragOver={(event) => event.preventDefault()}
            onDrop={() => dropWidget(widget)}
            onDragEnd={() => setDraggedWidget(null)}
            className={`min-w-0 space-y-2 ${widget === 'balance' ? 'lg:col-span-2' : ''} ${widget === 'prices' || widget === 'usage_leaderboard' ? 'lg:col-span-3' : ''} ${draggedWidget === widget ? 'opacity-50' : ''}`}
          >
            <div className="flex items-center justify-between gap-2">
              <span
                title="Drag to reorder"
                className="inline-flex cursor-grab items-center gap-1 text-xs text-muted-foreground active:cursor-grabbing"
              >
                <GripVertical className="h-4 w-4" aria-hidden="true" />
                {WIDGET_LABELS[widget]}
              </span>
              <div className="flex gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-11 w-11"
                  aria-label={`Move ${WIDGET_LABELS[widget]} up`}
                  disabled={controlsDisabled || index === 0}
                  onClick={() => moveWidget(widget, -1)}
                >
                  <ChevronUp className="h-4 w-4" aria-hidden="true" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-11 w-11"
                  aria-label={`Move ${WIDGET_LABELS[widget]} down`}
                  disabled={controlsDisabled || index === layout.length - 1}
                  onClick={() => moveWidget(widget, 1)}
                >
                  <ChevronDown className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            </div>
            {renderWidget(widget)}
          </div>
        ))}
      </div>
    </section>
  )
}
