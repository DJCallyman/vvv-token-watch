'use client'

import { useState } from 'react'
import { Model } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatNumber } from '@/lib/utils'
import { ChevronDown, ChevronUp, Cpu, Zap, Clock, DollarSign, AlertTriangle } from 'lucide-react'
import { cn, getTypeColor } from '@/lib/utils'

interface ModelCardProps {
  model: Model
}

export function ModelCard({ model }: ModelCardProps) {
  const [expanded, setExpanded] = useState(false)

  const modelSpec = model.model_spec || model.spec || {}
  const flatModel = model as unknown as Record<string, unknown>
  const contextLength = modelSpec.availableContextTokens || flatModel.context_window as number | undefined
  const maxTokens = modelSpec.maxCompletionTokens || model.spec?.max_output_tokens
  const pricing = modelSpec.pricing || {
    input: flatModel.input_price_usd != null ? { usd: flatModel.input_price_usd } : undefined,
    output: flatModel.output_price_usd != null ? { usd: flatModel.output_price_usd } : undefined,
    cache_input: flatModel.cache_input_price_usd != null ? { usd: flatModel.cache_input_price_usd } : undefined,
    cache_write: flatModel.cache_write_price_usd != null ? { usd: flatModel.cache_write_price_usd } : undefined,
    generation: flatModel.generation_price_usd != null ? { usd: flatModel.generation_price_usd } : undefined,
  }

  const traitsRaw = modelSpec.traits || model.spec?.traits || {}
  const traits = Array.isArray(traitsRaw) ? traitsRaw : Object.keys(traitsRaw)

  const rawCapabilities = flatModel.capabilities
  const capabilities = modelSpec.capabilities || (Array.isArray(rawCapabilities)
    ? Object.fromEntries(rawCapabilities.map((cap: string) => [cap, true]))
    : {})
  const capabilityKeys = Object.keys(capabilities)
  const deprecation = (modelSpec.deprecation || flatModel.deprecation) as {
    removesAt?: string
    replacementModelId?: string
    autoRemap?: boolean
    startsAt?: string
    date?: string
  } | undefined | null
  const retirementDate = deprecation?.removesAt || deprecation?.date || deprecation?.startsAt
  const isRetiring = Boolean(retirementDate || deprecation?.replacementModelId)

  return (
    <Card className="hover:border-primary/50 transition-colors">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base font-semibold truncate" title={model.id}>
              {model.id}
            </CardTitle>
            {model.owned_by && (
              <p className="text-xs text-muted-foreground mt-0.5">by {model.owned_by}</p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {isRetiring && (
              <Badge
                variant="destructive"
                className="gap-1"
                title={
                  retirementDate
                    ? `Retiring ${retirementDate}${deprecation?.replacementModelId ? ` → ${deprecation.replacementModelId}` : ''}`
                    : 'Model is being retired'
                }
              >
                <AlertTriangle className="w-3 h-3" />
                Retiring
              </Badge>
            )}
            <Badge
              variant="outline"
              className={cn(getTypeColor(model.type || model.model_type || 'unknown'))}
            >
              {model.type || model.model_type || 'unknown'}
            </Badge>
          </div>
        </div>
        {isRetiring && (
          <div className="mt-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
            {retirementDate && <p>Retirement date: {retirementDate}</p>}
            {deprecation?.replacementModelId && (
              <p className="mt-1">
                Replacement model:{' '}
                <span className="font-medium text-foreground">{deprecation.replacementModelId}</span>
              </p>
            )}
            {deprecation?.autoRemap && deprecation?.replacementModelId && (
              <p className="mt-1 text-muted-foreground">
                Will auto-switch to {deprecation.replacementModelId}
                {retirementDate ? ` on ${retirementDate}` : ''}.
              </p>
            )}
          </div>
        )}
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-muted-foreground" />
            <span className="text-muted-foreground">Context:</span>
            <span className="font-medium">
              {contextLength ? formatNumber(contextLength) : '—'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-muted-foreground" />
            <span className="text-muted-foreground">Max Output:</span>
            <span className="font-medium">
              {maxTokens ? formatNumber(maxTokens) : '—'}
            </span>
          </div>
        </div>

        {traits.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1">
            {traits.slice(0, expanded ? undefined : 4).map((trait) => (
              <Badge key={trait} variant="secondary" className="text-xs">
                {trait}
              </Badge>
            ))}
            {traits.length > 4 && !expanded && (
              <span className="text-xs text-muted-foreground">
                +{traits.length - 4} more
              </span>
            )}
          </div>
        )}

        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-3 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-3 h-3" />
              Show less
            </>
          ) : (
            <>
              <ChevronDown className="w-3 h-3" />
              Show details
            </>
          )}
        </button>

        {expanded && (
          <div className="mt-4 pt-4 border-t border-border space-y-4">
            {(pricing.input || pricing.output) ? (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <DollarSign className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Pricing (per 1M tokens)</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="rounded-lg bg-muted/50 p-2">
                    <p className="text-xs text-muted-foreground">Input</p>
                    <p className="font-medium">
                      {pricing.input != null
                        ? typeof pricing.input === 'object' && 'usd' in pricing.input
                          ? `$${Number(pricing.input.usd ?? 0).toFixed(2)}`
                          : String(pricing.input)
                        : '—'}
                    </p>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-2">
                    <p className="text-xs text-muted-foreground">Output</p>
                    <p className="font-medium">
                      {pricing.output != null
                        ? typeof pricing.output === 'object' && 'usd' in pricing.output
                          ? `$${Number(pricing.output.usd ?? 0).toFixed(2)}`
                          : String(pricing.output)
                        : '—'}
                    </p>
                  </div>
                </div>
              </div>
            ) : null}

            {capabilityKeys.length > 0 && (
              <div>
                <p className="text-sm font-medium mb-2">Capabilities</p>
                <div className="flex flex-wrap gap-1">
                  {capabilityKeys.map((cap) => (
                    <Badge key={cap} variant="outline" className="text-xs">
                      {cap}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {traits.length > 0 && (
              <div>
                <p className="text-sm font-medium mb-2">All Traits</p>
                <div className="flex flex-wrap gap-1">
                  {traits.map((trait) => (
                    <Badge key={trait} variant="secondary" className="text-xs">
                      {trait}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
              {model.created && (
                <div>
                  <span>Created: </span>
                  <span className="font-medium">
                    {new Date(model.created * 1000).toLocaleDateString()}
                  </span>
                </div>
              )}
              {model.object && (
                <div>
                  <span>Type: </span>
                  <span className="font-medium">{model.object}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}