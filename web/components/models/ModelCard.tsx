'use client'

import { useState } from 'react'
import { Model } from '@/lib/hooks'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { formatNumber } from '@/lib/utils'
import { ChevronDown, ChevronUp, Cpu, Zap, Clock, DollarSign } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ModelCardProps {
  model: Model
}

export function ModelCard({ model }: ModelCardProps) {
  const [expanded, setExpanded] = useState(false)

  const modelSpec = model.model_spec || model.spec || {}
  const contextLength = modelSpec.availableContextTokens || model.spec?.context_length
  const maxTokens = modelSpec.maxCompletionTokens || model.spec?.max_output_tokens
  const pricing = modelSpec.pricing || model.spec?.pricing || {}
  
  const traitsRaw = modelSpec.traits || model.spec?.traits || {}
  const traits = Array.isArray(traitsRaw) ? traitsRaw : Object.keys(traitsRaw)
  
  const capabilities = modelSpec.capabilities || model.spec?.capabilities || {}
  const capabilityKeys = Object.keys(capabilities)

  const getTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'text':
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20'
      case 'image':
        return 'bg-purple-500/10 text-purple-500 border-purple-500/20'
      case 'audio':
        return 'bg-orange-500/10 text-orange-500 border-orange-500/20'
      default:
        return 'bg-gray-500/10 text-gray-500 border-gray-500/20'
    }
  }

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
          <Badge 
            variant="outline" 
            className={cn("shrink-0", getTypeColor(model.type))}
          >
            {model.type}
          </Badge>
        </div>
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
                      {pricing.input
                        ? typeof pricing.input === 'object' && 'usd' in pricing.input
                          ? `$${(pricing.input.usd ?? 0).toFixed(2)}`
                          : String(pricing.input)
                        : '—'}
                    </p>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-2">
                    <p className="text-xs text-muted-foreground">Output</p>
                    <p className="font-medium">
                      {pricing.output
                        ? typeof pricing.output === 'object' && 'usd' in pricing.output
                          ? `$${(pricing.output.usd ?? 0).toFixed(2)}`
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