'use client'

import { Sparkles, Loader2 } from 'lucide-react'
import { useModelTraits } from '@/lib/hooks'
import type { TraitModelType } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { cn } from '@/lib/utils'

export interface TraitsPanelProps {
  /** Model type to fetch traits for. Defaults to "text". */
  modelType?: TraitModelType
  /** Called when a user clicks a trait to filter the table to that model. */
  onPickModel?: (modelId: string) => void
  /** Currently-selected model id (highlighted pill). */
  selectedModelId?: string | null
  /** Optional className. */
  className?: string
}

export function TraitsPanel({
  modelType = 'text',
  onPickModel,
  selectedModelId,
  className,
}: TraitsPanelProps) {
  const { data, isLoading, isError } = useModelTraits(modelType)

  const traits = data?.data ?? {}
  const traitEntries = Object.entries(traits).filter(([, id]) => !!id)

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Sparkles className="w-4 h-4 text-primary" />
            Venice Recommended
          </CardTitle>
          <CardDescription>Trait → fastest/default/…</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading trait recommendations…
          </div>
        </CardContent>
      </Card>
    )
  }

  if (isError) {
    return null
  }

  if (traitEntries.length === 0) {
    return null
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="w-4 h-4 text-primary" />
          Venice Recommended
        </CardTitle>
        <CardDescription>
          Tap a trait to filter to that model. Type:{' '}
          <span className="font-medium text-foreground">{modelType}</span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          {traitEntries.map(([trait, modelId]) => {
            const isSelected = selectedModelId === modelId
            return (
              <button
                key={trait}
                type="button"
                onClick={() => onPickModel?.(modelId)}
                disabled={!onPickModel}
                className={cn(
                  'group inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition-colors',
                  isSelected
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-input hover:bg-accent',
                  !onPickModel && 'cursor-default hover:bg-transparent',
                )}
                aria-pressed={isSelected}
                title={`Use ${modelId} for ${trait}`}
              >
                <span className="font-medium capitalize">{trait}</span>
                <span
                  className={cn(
                    'font-mono text-xs',
                    isSelected ? 'text-primary/70' : 'text-muted-foreground',
                  )}
                >
                  {modelId}
                </span>
              </button>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
