'use client'

import { useState, useMemo, useCallback, useEffect } from 'react'
import { Model } from '@/lib/hooks'
import {
  ColumnDefinition,
  getColumnsForType,
  loadColumnPreferences,
  saveColumnPreferences,
  SortConfig,
  ModelType,
} from './columnConfig'
import { ChevronUp, ChevronDown, Settings2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ModelsComparisonTableProps {
  models: Model[]
  modelType: ModelType
  onOpenColumnSelector: () => void
  /** Optional external hidden-column set (kept in sync with ColumnSelector) */
  hiddenColumnsOverride?: Set<string>
}

const typeIcons: Record<string, string> = {
  text: '💬',
  image: '🖼️',
  video: '🎬',
  tts: '🔊',
  asr: '🎙️',
  embedding: '🔢',
  upscale: '📈',
  inpaint: '🎨',
}

function getModelType(model: Model): ModelType {
  const type = (model.type || model.model_type)?.toLowerCase()
  if (type === 'text' || type === 'image' || type === 'video' || 
      type === 'tts' || type === 'asr' || type === 'embedding' || 
      type === 'upscale' || type === 'inpaint') {
    return type as ModelType
  }
  return 'all'
}

const CAPABILITY_ALIASES: Record<string, string[]> = {
  vision: ['supportsVision', 'vision'],
  functions: ['supportsFunctionCalling', 'function_calling', 'functions'],
  web_search: ['supportsWebSearch', 'web_search'],
  reasoning: ['supportsReasoning', 'reasoning'],
  logprobs: ['supportsLogProbs', 'logprobs'],
  response_schema: ['supportsResponseSchema', 'response_schema'],
  optimized_for_code: ['optimizedForCode', 'optimized_for_code'],
  audio_input: ['supportsAudioInput', 'audio_input'],
  video_input: ['supportsVideoInput', 'video_input'],
}

function hasCapability(capabilities: Record<string, unknown>, columnKey: string): boolean {
  const aliases = CAPABILITY_ALIASES[columnKey] || [columnKey]
  return aliases.some((key) => Boolean(capabilities[key]))
}

function getCellValue(model: Model, columnKey: string): { display: string; sortValue: unknown } {
  const modelSpec = model.model_spec || model.spec || {}
  const flatModel = model as unknown as Record<string, unknown>
  // Support both full Venice model_spec and flat CachedModel list payloads
  const flatCapabilities: Record<string, boolean> = {}
  const rawCapabilities = flatModel.capabilities
  if (Array.isArray(rawCapabilities)) {
    rawCapabilities.forEach((cap: string) => { flatCapabilities[cap] = true })
  } else if (rawCapabilities && typeof rawCapabilities === 'object') {
    Object.entries(rawCapabilities as Record<string, unknown>).forEach(([key, value]) => {
      flatCapabilities[key] = Boolean(value)
    })
  }
  const capabilities = {
    ...flatCapabilities,
    ...(modelSpec.capabilities || {}),
  } as Record<string, unknown>
  const traits = modelSpec.traits || {}
  const constraints = modelSpec.constraints || {}
  const pricing = modelSpec.pricing || {}
  const modelType = getModelType(model)

  let display = '—'
  let sortValue: unknown = 0

  const getContextLength = () =>
    modelSpec.availableContextTokens ||
    modelSpec.context_length ||
    (flatModel.context_window as number | undefined) ||
    (flatModel.context_length as number | undefined)
  const getMaxTokens = () => modelSpec.maxCompletionTokens || model.spec?.max_output_tokens
  const getPrivacy = () => modelSpec.privacy || model.spec?.privacy || flatModel.privacy

  switch (columnKey) {
    case 'model':
      display = model.id
      sortValue = model.id
      break

    case 'type':
      const icon = typeIcons[modelType] || '❓'
      display = `${icon} ${modelType}`
      sortValue = modelType
      break

    case 'context':
    case 'specs':
      if (modelType === 'text') {
        const ctx = getContextLength()
        display = ctx ? ctx.toLocaleString() : '—'
        sortValue = ctx || 0
      } else if (modelType === 'image' || modelType === 'upscale' || modelType === 'inpaint') {
        const steps = constraints.steps?.max || constraints.steps?.default
        const promptLimit = constraints.promptCharacterLimit
        const parts = []
        if (steps) parts.push(`Steps: ${steps}`)
        if (promptLimit) parts.push(`Prompt: ${promptLimit}`)
        display = parts.join(', ') || 'Standard'
        sortValue = steps || 0
      } else if (modelType === 'tts' || modelType === 'asr') {
        const voices = modelSpec.voices || model.spec?.voices || modelSpec.supportedVoices || model.spec?.supportedVoices || []
        display = voices.length ? `${voices.length} voices` : 'Multiple voices'
        sortValue = voices.length || 0
      } else if (modelType === 'embedding') {
        const dims = modelSpec.dimensions || model.spec?.dimensions || modelSpec.embeddingDimensions || model.spec?.embeddingDimensions
        display = dims ? `Dim: ${dims}` : '—'
        sortValue = dims || 0
      } else if (modelType === 'video') {
        const durations = constraints.durations || []
        display = durations.length ? durations.join(', ') : 'Standard'
        sortValue = durations.length || 0
      }
      break

    case 'quantization':
      const quant = String(capabilities.quantization || '')
      display = quant && quant !== 'not-available' ? quant : '—'
      sortValue = quant || ''
      break

    case 'date_added':
      if (model.created) {
        const date = new Date(model.created * 1000)
        display = date.toLocaleDateString()
        sortValue = model.created
      }
      break

    case 'vision':
    case 'functions':
    case 'web_search':
    case 'reasoning':
    case 'logprobs':
    case 'response_schema':
    case 'optimized_for_code':
    case 'audio_input':
    case 'video_input':
      if (modelType === 'text') {
        const enabled = hasCapability(capabilities, columnKey)
        display = enabled ? '✓' : '✗'
        sortValue = enabled ? 1 : 0
      } else {
        display = '—'
        sortValue = 0
      }
      break

    case 'input_price':
    case 'price':
      if (modelType === 'text' || modelType === 'embedding') {
        const inputValue = pricing.input ?? (model as unknown as Record<string, unknown>).input_price_usd
        let inputCost: number | null = null
        if (typeof inputValue === 'object' && inputValue !== null && 'usd' in inputValue && inputValue.usd !== undefined) {
          inputCost = inputValue.usd as number
        } else if (typeof inputValue === 'number') {
          inputCost = inputValue
        }
        if (inputCost !== null && inputCost > 0) {
          display = `$${inputCost.toFixed(2)}`
          sortValue = inputCost
        } else if (typeof inputValue === 'string') {
          display = inputValue
          sortValue = 0
        }
      } else if (modelType === 'tts') {
        const inputValue = pricing.input
        let perChar: number | null = null
        if (typeof inputValue === 'object' && inputValue !== null && 'usd' in inputValue && inputValue.usd !== undefined) {
          perChar = inputValue.usd
        } else if (typeof inputValue === 'number') {
          perChar = inputValue
        }
        if (perChar !== null && perChar > 0) {
          display = `$${perChar.toFixed(2)}/1M`
          sortValue = perChar
        } else if (typeof inputValue === 'string') {
          display = inputValue
          sortValue = 0
        }
      } else if (modelType === 'asr') {
        const inputValue = pricing.input
        let perMin: number | null = null
        if (typeof inputValue === 'object' && inputValue !== null && 'usd' in inputValue && inputValue.usd !== undefined) {
          perMin = inputValue.usd
        } else if (typeof inputValue === 'number') {
          perMin = inputValue
        }
        if (perMin !== null && perMin > 0) {
          display = `$${perMin.toFixed(3)}/min`
          sortValue = perMin
        } else if (typeof inputValue === 'string') {
          display = inputValue
          sortValue = 0
        }
      }
      break

    case 'output_price':
      if (modelType === 'text') {
        const outputValue = pricing.output ?? (model as unknown as Record<string, unknown>).output_price_usd
        let outputCost: number | null = null
        if (typeof outputValue === 'object' && outputValue !== null && 'usd' in outputValue && outputValue.usd !== undefined) {
          outputCost = outputValue.usd as number
        } else if (typeof outputValue === 'number') {
          outputCost = outputValue
        }
        if (outputCost !== null && outputCost > 0) {
          display = `$${outputCost.toFixed(2)}`
          sortValue = outputCost
        } else if (typeof outputValue === 'string') {
          display = outputValue
          sortValue = 0
        }
      }
      break

    case 'cache_input':
      const cacheInputValue = pricing.cache_input ?? (model as unknown as Record<string, unknown>).cache_input_price_usd
      let cacheInput: number | null = null
      if (typeof cacheInputValue === 'object' && cacheInputValue !== null && 'usd' in cacheInputValue && cacheInputValue.usd !== undefined) {
        cacheInput = cacheInputValue.usd as number
      } else if (typeof cacheInputValue === 'number') {
        cacheInput = cacheInputValue
      }
      if (cacheInput !== null && cacheInput > 0) {
        display = `$${cacheInput.toFixed(2)}`
        sortValue = cacheInput
      } else if (typeof cacheInputValue === 'string') {
        display = cacheInputValue
        sortValue = 0
      }
      break

    case 'cache_write':
      const cacheWriteValue = pricing.cache_write ?? (model as unknown as Record<string, unknown>).cache_write_price_usd
      let cacheWrite: number | null = null
      if (typeof cacheWriteValue === 'object' && cacheWriteValue !== null && 'usd' in cacheWriteValue && cacheWriteValue.usd !== undefined) {
        cacheWrite = cacheWriteValue.usd as number
      } else if (typeof cacheWriteValue === 'number') {
        cacheWrite = cacheWriteValue
      }
      if (cacheWrite !== null && cacheWrite > 0) {
        display = `$${cacheWrite.toFixed(2)}`
        sortValue = cacheWrite
      } else if (typeof cacheWriteValue === 'string') {
        display = cacheWriteValue
        sortValue = 0
      }
      break

    case 'privacy':
      const privacyVal = getPrivacy()
      if (privacyVal && typeof privacyVal === 'string') {
        display = privacyVal
        sortValue = privacyVal
      } else if (privacyVal) {
        display = String(privacyVal)
        sortValue = String(privacyVal)
      }
      break

    case 'resolutions':
      const resolutions = constraints.resolutions || []
      if (resolutions.length > 0) {
        display = resolutions.slice(0, 3).join(', ') + (resolutions.length > 3 ? '...' : '')
        sortValue = resolutions.length
      } else {
        display = 'Standard'
        sortValue = 0
      }
      break

    case 'steps':
      const steps = constraints.steps?.max || constraints.steps?.default
      display = steps ? String(steps) : '—'
      sortValue = steps || 0
      break

    case 'prompt_limit':
      const limit = constraints.promptCharacterLimit
      display = limit ? String(limit) : '—'
      sortValue = limit || 0
      break

    case 'generation_price':
      const genPrice = pricing.generation?.usd || pricing.perImage?.usd || (model as unknown as Record<string, unknown>).generation_price_usd
      const resPricing = pricing.resolutions || {}
      if (genPrice && typeof genPrice === 'number' && genPrice > 0) {
        const suffix = modelType === 'video' ? '/video' : '/img'
        display = `$${genPrice.toFixed(4)}${suffix}`
        sortValue = genPrice
      } else if (Object.keys(resPricing).length > 0) {
        const prices = Object.values(resPricing).map((p: unknown) => 
          typeof p === 'object' && p !== null && 'usd' in p ? (p as { usd: number }).usd : 0
        )
        if (prices.length > 0) {
          const minPrice = Math.min(...prices)
          const maxPrice = Math.max(...prices)
          display = minPrice === maxPrice 
            ? `$${minPrice.toFixed(2)}/gen` 
            : `$${minPrice.toFixed(2)}-$${maxPrice.toFixed(2)}/gen`
          sortValue = minPrice
        }
      } else if (modelType === 'video') {
        display = 'Variable'
        sortValue = 999999
      } else {
        display = 'See pricing'
        sortValue = 999999
      }
      break

    case 'video_type':
      const videoModelType = constraints.model_type
      if (videoModelType === 'image-to-video') {
        display = 'img→vid'
        sortValue = 'image-to-video'
      } else if (videoModelType === 'text-to-video') {
        display = 'text→vid'
        sortValue = 'text-to-video'
      } else {
        const modelId = model.id?.toLowerCase()
        if (modelId.includes('image') || modelId.includes('img') || modelId.includes('i2v')) {
          display = 'img→vid'
          sortValue = 'image-to-video'
        } else {
          display = 'text→vid'
          sortValue = 'text-to-video'
        }
      }
      break

    case 'durations':
      const durations = constraints.durations || []
      if (durations.length > 0) {
        display = durations.map(d => String(d).endsWith('s') ? d : `${d}s`).join(', ')
        sortValue = durations.length
      } else {
        display = 'Standard'
        sortValue = 0
      }
      break

    case 'audio':
      const hasAudio = constraints.audio
      display = hasAudio ? '✓' : '✗'
      sortValue = hasAudio ? 1 : 0
      break

    case 'audio_configurable':
      const audioConfig = constraints.audio_configurable
      display = audioConfig ? '✓' : '✗'
      sortValue = audioConfig ? 1 : 0
      break

    case 'aspect_ratios':
      const ratios = constraints.aspect_ratios || []
      if (ratios.length > 0) {
        display = ratios.slice(0, 4).join(', ')
        sortValue = ratios.length
      } else {
        display = '—'
        sortValue = 0
      }
      break

    case 'base_price':
    case 'audio_price':
      display = '—'
      sortValue = 0
      break

    case 'voices':
      const voices = modelSpec.voices || modelSpec.supportedVoices || []
      display = voices.length ? `${voices.length} voices` : 'Multiple'
      sortValue = voices.length || 999
      break

    case 'dimensions':
      const dims = modelSpec.dimensions || modelSpec.embeddingDimensions
      display = dims ? String(dims) : '—'
      sortValue = dims || 0
      break

    case 'upscale_factors':
      const factors = constraints.upscale_factors || constraints.factors || []
      display = factors.length ? factors.join(', ') : '—'
      sortValue = factors.length || 0
      break

    case 'upscale_price':
    case 'inpaint_price':
      const upPrice = pricing.upscale?.usd || pricing.inpaint?.usd || pricing.generation?.usd || (model as unknown as Record<string, unknown>).generation_price_usd
      if (upPrice && typeof upPrice === 'number') {
        display = `$${upPrice.toFixed(4)}`
        sortValue = upPrice
      }
      break

    default:
      const traitValue = Array.isArray(traits) ? traits.find(t => t === columnKey) : (traits as Record<string, unknown>)?.[columnKey]
      const capValue = capabilities[columnKey]
      if (traitValue !== undefined) {
        display = String(traitValue)
        sortValue = traitValue
      } else if (capValue !== undefined) {
        if (typeof capValue === 'boolean') {
          display = capValue ? '✓' : '✗'
          sortValue = capValue ? 1 : 0
        } else {
          display = String(capValue)
          sortValue = capValue
        }
      }
  }

  return { display, sortValue }
}

export function ModelsComparisonTable({
  models,
  modelType,
  onOpenColumnSelector,
  hiddenColumnsOverride,
}: ModelsComparisonTableProps) {
  const [sortConfig, setSortConfig] = useState<SortConfig>({ key: 'model', direction: 'asc' })
  const [hiddenColumns, setHiddenColumns] = useState<Set<string>>(() => 
    loadColumnPreferences(modelType)
  )

  // Reload per-type column preferences when the selected model type changes
  useEffect(() => {
    setHiddenColumns(loadColumnPreferences(modelType))
  }, [modelType])

  // Stay in sync when ColumnSelector updates preferences
  useEffect(() => {
    if (hiddenColumnsOverride) {
      setHiddenColumns(new Set(hiddenColumnsOverride))
    }
  }, [hiddenColumnsOverride])

  const allColumns = useMemo(() => getColumnsForType(modelType), [modelType])

  const visibleColumns = useMemo(() => {
    return allColumns.filter(col => !hiddenColumns.has(col.key))
  }, [allColumns, hiddenColumns])

  const sortedModels = useMemo(() => {
    const sorted = [...models]
    sorted.sort((a, b) => {
      const aVal = getCellValue(a, sortConfig.key).sortValue
      const bVal = getCellValue(b, sortConfig.key).sortValue

      let comparison = 0
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        comparison = aVal - bVal
      } else if (typeof aVal === 'string' && typeof bVal === 'string') {
        comparison = aVal.localeCompare(bVal)
      } else if (typeof aVal === 'number') {
        comparison = -1
      } else if (typeof bVal === 'number') {
        comparison = 1
      } else {
        comparison = String(aVal).localeCompare(String(bVal))
      }

      return sortConfig.direction === 'asc' ? comparison : -comparison
    })
    return sorted
  }, [models, sortConfig])

  const handleSort = useCallback((key: string) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }))
  }, [])

  const toggleColumn = useCallback((key: string) => {
    setHiddenColumns(prev => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      saveColumnPreferences(modelType, next)
      return next
    })
  }, [modelType])

  const isColumnHidden = useCallback((key: string) => hiddenColumns.has(key), [hiddenColumns])

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <div className="flex items-center justify-end p-2 bg-muted/50 border-b border-border">
        <button
          onClick={onOpenColumnSelector}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md hover:bg-muted transition-colors"
        >
          <Settings2 className="w-4 h-4" />
          Columns
        </button>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-muted/50 border-b border-border">
            {visibleColumns.map((column) => (
              <th
                key={column.key}
                className={cn(
                  "px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap",
                  column.sortable && "cursor-pointer hover:text-foreground select-none"
                )}
                style={{ minWidth: column.minWidth }}
                onClick={() => column.sortable && handleSort(column.key)}
                title={column.tooltip}
              >
                <div className="flex items-center gap-1">
                  {column.header}
                  {column.sortable && (
                    <span className="text-xs ml-1">
                      {sortConfig.key === column.key ? (
                        sortConfig.direction === 'asc' ? (
                          <ChevronUp className="w-3 h-3" />
                        ) : (
                          <ChevronDown className="w-3 h-3" />
                        )
                      ) : (
                        <span className="opacity-30">↕</span>
                      )}
                    </span>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedModels.map((model) => (
            <tr
              key={model.id}
              className="border-b border-border hover:bg-muted/30 transition-colors"
            >
              {visibleColumns.map((column) => {
                const { display, sortValue } = getCellValue(model, column.key)
                const isBoolean = typeof sortValue === 'number' && (sortValue === 0 || sortValue === 1) && 
                  ['vision', 'functions', 'web_search', 'reasoning', 'logprobs', 'response_schema', 
                   'optimized_for_code', 'audio_input', 'video_input', 'audio', 'audio_configurable'].includes(column.key)
                
                return (
                  <td
                    key={column.key}
                    className={cn(
                      "px-3 py-2 whitespace-nowrap",
                      column.key === 'model' && "font-medium"
                    )}
                  >
                    {isBoolean ? (
                      <span className={cn(
                        "inline-flex items-center justify-center w-5 h-5 rounded text-xs font-medium",
                        sortValue === 1 
                          ? "bg-success/10 text-success" 
                          : "bg-destructive/10 text-destructive"
                      )}>
                        {display}
                      </span>
                    ) : (
                      display
                    )}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {sortedModels.length === 0 && (
        <div className="py-12 text-center text-muted-foreground">
          No models match your filters
        </div>
      )}
    </div>
  )
}