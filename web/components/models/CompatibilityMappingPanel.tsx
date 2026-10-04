'use client'

import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'
import { useModelCompatibilityMapping } from '@/lib/hooks'
import type { TraitModelType } from '@/lib/api'

export function CompatibilityMappingPanel({ modelType }: { modelType: TraitModelType }) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const { data, isLoading, isError } = useModelCompatibilityMapping(modelType, open)

  const mappings = useMemo(() => {
    const query = search.trim().toLowerCase()
    return Object.entries(data?.data ?? {})
      .filter(([alias, modelId]) => !query || `${alias} ${modelId}`.toLowerCase().includes(query))
      .sort(([left], [right]) => left.localeCompare(right))
  }, [data, search])

  return (
    <section className="border-y border-border py-3">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="text-sm font-medium hover:text-primary"
      >
        {open ? 'Hide compatibility IDs' : 'Show compatibility IDs'}
      </button>
      {open && (
        <div className="mt-3 space-y-3">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              aria-label="Filter compatibility IDs"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Filter aliases or Venice model IDs"
              className="w-full rounded-md border border-input bg-background py-2 pl-9 pr-3 text-sm"
            />
          </div>
          {isLoading && <p className="text-sm text-muted-foreground">Loading mappings…</p>}
          {isError && <p role="alert" className="text-sm text-destructive">Could not load compatibility mappings.</p>}
          {!isLoading && !isError && (
            <div className="max-h-64 overflow-auto rounded-md border border-border">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-muted text-left">
                  <tr>
                    <th className="px-3 py-2 font-medium">Compatible ID</th>
                    <th className="px-3 py-2 font-medium">Venice model ID</th>
                  </tr>
                </thead>
                <tbody>
                  {mappings.map(([alias, modelId]) => (
                    <tr key={alias} className="border-t border-border">
                      <td className="px-3 py-2 font-mono text-xs">{alias}</td>
                      <td className="px-3 py-2 font-mono text-xs">{modelId}</td>
                    </tr>
                  ))}
                  {mappings.length === 0 && (
                    <tr>
                      <td colSpan={2} className="px-3 py-4 text-center text-muted-foreground">
                        No matching model IDs.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  )
}