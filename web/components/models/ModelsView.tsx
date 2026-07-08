'use client'

import { useState, useMemo } from 'react'
import { useModels, Model } from '@/lib/hooks'
import { Card, CardContent } from '@/components/ui/card'
import { ModelCard } from './ModelCard'
import { ModelsComparisonTable } from './ModelsComparisonTable'
import { ColumnSelector } from './ColumnSelector'
import { ModelAnalytics } from './ModelAnalytics'
import { Search, Filter, X, LayoutGrid, List, Table, ChevronDown, ChevronUp, DollarSign, BarChart3, ListX } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ModelType } from './columnConfig'

type ViewMode = 'grid' | 'list' | 'table'
type SortMode = 'name' | 'type' | 'context'
type TabMode = 'browse' | 'analytics'

interface CapabilityFilter {
  vision: boolean
  functions: boolean
  web_search: boolean
  reasoning: boolean
}

export function ModelsView() {
  const { data, isLoading, isError } = useModels()
  const [tab, setTab] = useState<TabMode>('browse')
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [traitFilter, setTraitFilter] = useState<string>('all')
  const [viewMode, setViewMode] = useState<ViewMode>('grid')
  const [sortMode, setSortMode] = useState<SortMode>('name')
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false)
  const [capabilityFilter, setCapabilityFilter] = useState<CapabilityFilter>({
    vision: false,
    functions: false,
    web_search: false,
    reasoning: false,
  })
  const [maxPriceFilter, setMaxPriceFilter] = useState<string>('')
  const [columnSelectorOpen, setColumnSelectorOpen] = useState(false)

  const models = useMemo(() => data?.models || [], [data])
  const types = useMemo(() => data?.types || [], [data])

  const allTraits = useMemo(() => {
    const traits = new Set<string>()
    models.forEach((model: Model) => {
      const modelSpec = model.model_spec || model.spec || {}
      const traitsRaw = modelSpec.traits || model.spec?.traits || {}
      if (Array.isArray(traitsRaw)) {
        traitsRaw.forEach((trait) => { traits.add(trait) })
      } else {
        Object.keys(traitsRaw).forEach((trait) => { traits.add(trait) })
      }
    })
    return Array.from(traits).sort()
  }, [models])

  const filteredModels = useMemo(() => {
    let result = [...models]

    if (search) {
      const searchLower = search.toLowerCase()
      result = result.filter((model: Model) => {
        const modelId = model.id.toLowerCase()
        const ownedBy = model.owned_by?.toLowerCase() || ''
        const modelSpec = model.model_spec || model.spec || {}
        const traitsRaw = modelSpec.traits || model.spec?.traits || {}
        const capabilities = modelSpec.capabilities || model.spec?.capabilities || {}
        
        const traits = Array.isArray(traitsRaw) ? traitsRaw.join(' ') : Object.keys(traitsRaw).join(' ')
        const capKeys = Object.keys(capabilities).join(' ').toLowerCase()
        
        return modelId.includes(searchLower) ||
               ownedBy.includes(searchLower) ||
               traits.toLowerCase().includes(searchLower) ||
               capKeys.includes(searchLower)
      })
    }

    if (typeFilter !== 'all') {
      result = result.filter((model: Model) => model.type === typeFilter)
    }

    if (traitFilter !== 'all') {
      result = result.filter((model: Model) => {
        const modelSpec = model.model_spec || model.spec || {}
        const traitsRaw = modelSpec.traits || model.spec?.traits || {}
        if (Array.isArray(traitsRaw)) {
          return traitsRaw.includes(traitFilter)
        }
        return traitFilter in traitsRaw
      })
    }

    const activeCapabilities = Object.entries(capabilityFilter)
      .filter(([, active]) => active)
      .map(([key]) => key)

    if (activeCapabilities.length > 0) {
      result = result.filter((model: Model) => {
        const modelSpec = model.model_spec || model.spec || {}
        const capabilities = modelSpec.capabilities || model.spec?.capabilities || {}
        return activeCapabilities.every(cap => {
          const capKey = cap === 'web_search' ? 'supportsWebSearch' : 
                         cap === 'vision' ? 'supportsVision' :
                         cap === 'functions' ? 'supportsFunctionCalling' :
                         cap === 'reasoning' ? 'supportsReasoning' : cap
          return capabilities[capKey as keyof typeof capabilities]
        })
      })
    }

    if (maxPriceFilter) {
      const maxPrice = parseFloat(maxPriceFilter)
      if (!Number.isNaN(maxPrice)) {
        result = result.filter((model: Model) => {
          const modelSpec = model.model_spec || model.spec || {}
          const pricing = modelSpec.pricing || model.spec?.pricing || {}
          const inputValue = pricing.input
          let inputPrice: number | null = null
          if (typeof inputValue === 'object' && inputValue !== null && 'usd' in inputValue && inputValue.usd !== undefined) {
            inputPrice = inputValue.usd
          } else if (typeof inputValue === 'number') {
            inputPrice = inputValue
          }
          const genPrice = pricing.generation?.usd ?? pricing.perImage?.usd ?? null
          
          if (inputPrice !== null && inputPrice > 0) {
            return inputPrice <= maxPrice
          }
          if (genPrice !== null && genPrice > 0) {
            return genPrice <= maxPrice
          }
          return true
        })
      }
    }

    result.sort((a: Model, b: Model) => {
      switch (sortMode) {
        case 'name':
          return a.id.localeCompare(b.id)
        case 'type':
          return a.type.localeCompare(b.type) || a.id.localeCompare(b.id)
        case 'context': {
          const aSpec = a.model_spec || a.spec || {}
          const bSpec = b.model_spec || b.spec || {}
          const aContext = aSpec.availableContextTokens || aSpec.context_length || 0
          const bContext = bSpec.availableContextTokens || bSpec.context_length || 0
          return bContext - aContext
        }
        default:
          return 0
      }
    })

    return result
  }, [models, search, typeFilter, traitFilter, sortMode, capabilityFilter, maxPriceFilter])

  const activeFilters = (typeFilter !== 'all' ? 1 : 0) + 
    (traitFilter !== 'all' ? 1 : 0) + 
    (search ? 1 : 0) +
    (Object.values(capabilityFilter).some(Boolean) ? 1 : 0) +
    (maxPriceFilter ? 1 : 0)

  const clearFilters = () => {
    setSearch('')
    setTypeFilter('all')
    setTraitFilter('all')
    setCapabilityFilter({ vision: false, functions: false, web_search: false, reasoning: false })
    setMaxPriceFilter('')
  }

  const toggleCapability = (key: keyof CapabilityFilter) => {
    setCapabilityFilter(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const modelTypeForTable: ModelType = useMemo(() => {
    if (typeFilter !== 'all' && ['text', 'image', 'video', 'tts', 'asr', 'embedding', 'upscale', 'inpaint'].includes(typeFilter)) {
      return typeFilter as ModelType
    }
    return 'all'
  }, [typeFilter])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Models</h1>
          <p className="text-sm text-muted-foreground">Loading models...</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i}>
              <CardContent className="h-40 flex items-center justify-center">
                <div className="animate-pulse text-muted-foreground">Loading...</div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Models</h1>
          <p className="text-sm text-muted-foreground">Failed to load models</p>
        </div>
        <Card>
          <CardContent className="h-40 flex items-center justify-center">
            <div className="text-destructive">Failed to load models. Please check your API connection.</div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Models</h1>
          <p className="text-sm text-muted-foreground">
            {tab === 'browse' ? `Browse ${models.length} Venice AI models` : 'Usage analytics and performance metrics'}
          </p>
        </div>
        <div className="flex items-center gap-1 border rounded-md p-1">
          <button
            onClick={() => setTab('browse')}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 text-sm rounded transition-colors",
              tab === 'browse' ? "bg-primary text-primary-foreground" : "hover:bg-muted"
            )}
          >
            <ListX className="w-4 h-4" />
            Browse
          </button>
          <button
            onClick={() => setTab('analytics')}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 text-sm rounded transition-colors",
              tab === 'analytics' ? "bg-primary text-primary-foreground" : "hover:bg-muted"
            )}
          >
            <BarChart3 className="w-4 h-4" />
            Analytics
          </button>
        </div>
      </div>

      {tab === 'analytics' ? (
        <ModelAnalytics />
      ) : (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search models, traits, capabilities..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="flex gap-2">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="all">All Types</option>
              {types.map((type) => (
                <option key={type} value={type}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </option>
              ))}
            </select>

            <select
              value={traitFilter}
              onChange={(e) => setTraitFilter(e.target.value)}
              className="px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="all">All Traits</option>
              {allTraits.map((trait) => (
                <option key={trait} value={trait}>
                  {trait}
                </option>
              ))}
            </select>

            <select
              value={sortMode}
              onChange={(e) => setSortMode(e.target.value as SortMode)}
              className="px-3 py-2 rounded-md border border-input bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="name">Sort by Name</option>
              <option value="type">Sort by Type</option>
              <option value="context">Sort by Context</option>
            </select>
          </div>
        </div>

        <button
          onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {showAdvancedFilters ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          Advanced Filters
          {Object.values(capabilityFilter).some(Boolean) && (
            <span className="ml-1 px-1.5 py-0.5 text-xs bg-primary/10 text-primary rounded">
              {Object.values(capabilityFilter).filter(Boolean).length}
            </span>
          )}
        </button>

        {showAdvancedFilters && (
          <div className="flex flex-wrap gap-4 p-4 rounded-lg border border-border bg-muted/30">
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">Capabilities</p>
              <div className="flex flex-wrap gap-2">
                {(['vision', 'functions', 'web_search', 'reasoning'] as const).map((cap) => (
                  <label
                    key={cap}
                    className={cn(
                      "flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md cursor-pointer border transition-colors",
                      capabilityFilter[cap]
                        ? "bg-primary/10 border-primary text-primary"
                        : "bg-background border-input hover:bg-muted"
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={capabilityFilter[cap]}
                      onChange={() => toggleCapability(cap)}
                      className="sr-only"
                    />
                    {cap === 'web_search' ? 'Web Search' : cap.charAt(0).toUpperCase() + cap.slice(1)}
                  </label>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">Max Input Price ($/1M)</p>
              <div className="relative">
                <DollarSign className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                <input
                  type="number"
                  placeholder="No limit"
                  value={maxPriceFilter}
                  onChange={(e) => setMaxPriceFilter(e.target.value)}
                  className="w-32 pl-8 pr-3 py-1.5 text-sm rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            </div>

            {(Object.values(capabilityFilter).some(Boolean) || maxPriceFilter) && (
              <button
                onClick={() => {
                  setCapabilityFilter({ vision: false, functions: false, web_search: false, reasoning: false })
                  setMaxPriceFilter('')
                }}
                className="self-end text-xs text-primary hover:underline"
              >
                Clear advanced
              </button>
            )}
          </div>
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {filteredModels.length} model{filteredModels.length !== 1 ? 's' : ''}
              {activeFilters > 0 && ` (filtered)`}
            </span>
            {activeFilters > 0 && (
              <button
                onClick={clearFilters}
                className="text-xs text-primary hover:underline"
              >
                Clear all
              </button>
            )}
          </div>

          <div className="flex items-center gap-1 border rounded-md p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={cn(
                "p-1.5 rounded",
                viewMode === 'grid' ? "bg-primary text-primary-foreground" : "hover:bg-muted"
              )}
              title="Grid view"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={cn(
                "p-1.5 rounded",
                viewMode === 'list' ? "bg-primary text-primary-foreground" : "hover:bg-muted"
              )}
              title="List view"
            >
              <List className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={cn(
                "p-1.5 rounded",
                viewMode === 'table' ? "bg-primary text-primary-foreground" : "hover:bg-muted"
              )}
              title="Table view"
            >
              <Table className="w-4 h-4" />
            </button>
          </div>
        </div>

      {filteredModels.length === 0 ? (
        <Card>
          <CardContent className="h-40 flex flex-col items-center justify-center gap-2">
            <Filter className="w-8 h-8 text-muted-foreground" />
            <p className="text-muted-foreground">No models match your filters</p>
            <button
              onClick={clearFilters}
              className="text-sm text-primary hover:underline"
            >
              Clear all filters
            </button>
          </CardContent>
        </Card>
      ) : viewMode === 'table' ? (
        <ModelsComparisonTable
          models={filteredModels}
          modelType={modelTypeForTable}
          onOpenColumnSelector={() => setColumnSelectorOpen(true)}
        />
      ) : viewMode === 'grid' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredModels.map((model: Model) => (
            <ModelCard key={model.id} model={model} />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {filteredModels.map((model: Model) => (
            <ModelListItem key={model.id} model={model} />
          ))}
        </div>
      )}

<ColumnSelector
        isOpen={columnSelectorOpen}
        onClose={() => setColumnSelectorOpen(false)}
        modelType={modelTypeForTable}
      />
      </div>
      )}
    </div>
  )
}

function ModelListItem({ model }: { model: Model }) {
  const modelSpec = model.model_spec || model.spec || {}
  const contextLength = modelSpec.availableContextTokens || model.spec?.context_length
  const maxTokens = modelSpec.maxCompletionTokens || model.spec?.max_output_tokens
  const pricing = modelSpec.pricing || model.spec?.pricing || {}

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
      <CardContent className="flex items-center gap-4 py-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium truncate">{model.id}</span>
            <span className={cn("text-xs px-2 py-0.5 rounded border", getTypeColor(model.type))}>
              {model.type}
            </span>
          </div>
          {model.owned_by && (
            <p className="text-xs text-muted-foreground">by {model.owned_by}</p>
          )}
        </div>
        <div className="flex items-center gap-6 text-sm text-muted-foreground">
          <div className="hidden sm:block">
            <span>Context: </span>
            <span className="font-medium text-foreground">
              {contextLength ? contextLength.toLocaleString() : '—'}
            </span>
          </div>
          <div className="hidden md:block">
            <span>Max: </span>
            <span className="font-medium text-foreground">
              {maxTokens ? maxTokens.toLocaleString() : '—'}
            </span>
          </div>
          {pricing.input && (
            <div className="hidden lg:block">
              <span>Input: </span>
              <span className="font-medium text-foreground">
                {pricing.input
                  ? typeof pricing.input === 'object' && 'usd' in pricing.input
                    ? `$${(pricing.input.usd ?? 0).toFixed(2)}`
                    : String(pricing.input)
                  : '—'}
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}