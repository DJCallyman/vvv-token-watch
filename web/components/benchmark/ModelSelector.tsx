'use client'

import { useState, useMemo } from 'react'
import { BenchmarkModel } from '@/lib/api'
import { useBenchmarkModels } from '@/lib/hooks'

interface Props {
  onSelectionChange: (models: string[] | null) => void // null = all models
}

export function ModelSelector({ onSelectionChange }: Props) {
  const [allModels, setAllModels] = useState(true)
  const [filter, setFilter] = useState('')
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const { data, isLoading } = useBenchmarkModels()
  const models = useMemo(() => data?.models ?? [], [data])

  const filtered = useMemo(() => {
    if (!filter) return models
    const q = filter.toLowerCase()
    return models.filter((m) => m.id?.toLowerCase().includes(q))
  }, [models, filter])

  const toggleAll = (checked: boolean) => {
    setAllModels(checked)
    if (checked) {
      setSelected(new Set())
      onSelectionChange(null)
    } else {
      // Default: select all when switching to manual mode
      const ids = models.map((m) => m.id)
      const newSet = new Set(ids)
      setSelected(newSet)
      onSelectionChange(ids)
    }
  }

  const toggleModel = (id: string, checked: boolean) => {
    const next = new Set(selected)
    if (checked) next.add(id)
    else next.delete(id)
    setSelected(next)
    onSelectionChange(next.size > 0 ? Array.from(next) : null)
  }

  const selectAll = () => {
    const ids = models.map((m) => m.id)
    setSelected(new Set(ids))
    onSelectionChange(ids)
  }

  const selectNone = () => {
    setSelected(new Set())
    onSelectionChange([])
  }

  return (
    <div className="space-y-3">
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={allModels}
          onChange={(e) => toggleAll(e.target.checked)}
          className="w-4 h-4 rounded border-border accent-primary"
        />
        <span className="text-sm font-medium text-foreground">
          All qualifying models
          {data && (
            <span className="ml-1 text-muted-foreground font-normal">
              ({data.count} private/anonymized)
            </span>
          )}
        </span>
      </label>

      {!allModels && (
        <div className="pl-6 space-y-2">
          <div className="flex items-center gap-2">
            <input
              type="text"
              placeholder="Filter models…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="flex-1 bg-muted/30 border border-border rounded-md text-sm px-3 py-1.5 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <button onClick={selectAll} className="text-xs text-primary hover:underline px-1">All</button>
            <button onClick={selectNone} className="text-xs text-muted-foreground hover:underline px-1">None</button>
          </div>

          {isLoading ? (
            <p className="text-xs text-muted-foreground">Loading models…</p>
          ) : (
            <div className="max-h-48 overflow-y-auto space-y-1 pr-1">
              {filtered.map((m: BenchmarkModel) => (
                <label key={m.id} className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={selected.has(m.id)}
                    onChange={(e) => toggleModel(m.id, e.target.checked)}
                    className="w-3.5 h-3.5 rounded border-border accent-primary shrink-0"
                  />
                  <span className="text-xs font-mono text-foreground group-hover:text-primary transition-colors truncate">
                    {m.id}
                  </span>
                  <span className={`text-xs px-1 rounded shrink-0 ${m.privacy === 'private' ? 'bg-blue-900/50 text-blue-300' : 'bg-purple-900/50 text-purple-300'}`}>
                    {m.privacy}
                  </span>
                  {m.deprecation?.removesAt && (
                    <span className="text-xs px-1 rounded shrink-0 bg-yellow-900/50 text-yellow-300" title={`Retiring ${m.deprecation.removesAt}${m.deprecation.replacementModelId ? ` → ${m.deprecation.replacementModelId}` : ''}`}>
                      retiring
                    </span>
                  )}
                  {m.pricing_input_usd != null && (
                    <span className="text-xs text-muted-foreground shrink-0">
                      ${m.pricing_input_usd.toFixed(2)}
                    </span>
                  )}
                </label>
              ))}
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            {selected.size} of {models.length} selected
          </p>
        </div>
      )}
    </div>
  )
}
