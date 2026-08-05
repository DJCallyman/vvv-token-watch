'use client'

import { useEffect, useMemo, useState } from 'react'
import { Search, Filter, X, RefreshCw, AlertTriangle, Users } from 'lucide-react'
import { useCharacters } from '@/lib/hooks'
import type {
  Character,
  CharacterSortBy,
  CharacterSortOrder,
  GetCharactersParams,
} from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CharacterCard } from './CharacterCard'
import { CharacterDetailDrawer } from './CharacterDetailDrawer'
import { cn } from '@/lib/utils'

const SORT_OPTIONS: { value: CharacterSortBy; label: string }[] = [
  { value: 'featured', label: 'Featured' },
  { value: 'highestRating', label: 'Highest rated' },
  { value: 'highlyRated', label: 'Highly rated' },
  { value: 'highlyRatedAndRecent', label: 'Highly rated & recent' },
  { value: 'imports', label: 'Most imports' },
  { value: 'mostRecent', label: 'Most recent' },
  { value: 'ratingCount', label: 'Most ratings' },
]

const SORT_ORDERS: { value: CharacterSortOrder; label: string }[] = [
  { value: 'desc', label: 'Descending' },
  { value: 'asc', label: 'Ascending' },
]

export function CharactersView() {
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<CharacterSortBy>('featured')
  const [sortOrder, setSortOrder] = useState<CharacterSortOrder>('desc')
  const [includeAdult, setIncludeAdult] = useState(false)
  const [webOnly, setWebOnly] = useState(false)
  const [selected, setSelected] = useState<Character | null>(null)

  // Debounce search to avoid hammering the upstream on every keystroke.
  const [debouncedSearch, setDebouncedSearch] = useState('')
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(t)
  }, [search])

  const queryParams = useMemo<GetCharactersParams>(
    () => {
      const params: GetCharactersParams = {
        sortBy,
        sortOrder,
        limit: 100,
      }
      const trimmed = debouncedSearch.trim()
      if (trimmed) params.search = trimmed
      if (webOnly) params.isWebEnabled = 'true'
      if (includeAdult) params.isAdult = 'true'
      return params
    },
    [debouncedSearch, sortBy, sortOrder, includeAdult, webOnly],
  )

  const { data, isLoading, isError, refetch, isFetching } = useCharacters(queryParams)

  const characters = useMemo(() => data?.data ?? [], [data])

  // Derive available tags from results so the filter pills reflect the
  // current set (Venice pre-filter may have already narrowed it).
  const availableTags = useMemo(() => {
    const tagSet = new Set<string>()
    characters.forEach((c) => c.tags.forEach((t) => tagSet.add(t)))
    return Array.from(tagSet).sort().slice(0, 20)
  }, [characters])

  const [tagFilter, setTagFilter] = useState<string | null>(null)

  const activeFilters =
    Number(!!debouncedSearch.trim()) +
    Number(tagFilter != null) +
    Number(webOnly) +
    Number(includeAdult)

  const clearFilters = () => {
    setSearch('')
    setTagFilter(null)
    setWebOnly(false)
    setIncludeAdult(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Users className="w-6 h-6" />
          Characters
        </h1>
        <div className="text-sm text-muted-foreground mt-1 flex items-center gap-2 flex-wrap">
          <span>Browse and search Venice AI characters</span>
          <Badge variant="outline" className="text-xs">
            Preview API
          </Badge>
        </div>
      </div>

      <Card>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search by name, description, or tags…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-10 py-2 rounded-md border border-input bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  aria-label="Clear search"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as CharacterSortBy)}
              className="px-3 py-2 rounded-md border border-input bg-background text-foreground"
              aria-label="Sort by"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  Sort: {opt.label}
                </option>
              ))}
            </select>
            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as CharacterSortOrder)}
              className="px-3 py-2 rounded-md border border-input bg-background text-foreground"
              aria-label="Sort order"
            >
              {SORT_ORDERS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => refetch()}
              disabled={isFetching}
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-2 text-sm hover:bg-accent disabled:opacity-50"
              aria-label="Refresh characters"
            >
              <RefreshCw className={cn('w-4 h-4', isFetching && 'animate-spin')} />
              Refresh
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Filter className="w-4 h-4 text-muted-foreground" />
            <ToggleChip
              active={webOnly}
              onToggle={() => setWebOnly((v) => !v)}
              label="Web enabled only"
            />
            <ToggleChip
              active={includeAdult}
              onToggle={() => setIncludeAdult((v) => !v)}
              label="Include adult"
              variant="warning"
            />
            {availableTags.length > 0 && (
              <div className="flex flex-wrap items-center gap-1 ml-2 border-l border-border pl-2">
                <span className="text-xs text-muted-foreground">Tags:</span>
                {availableTags.map((tag) => (
                  <button
                    key={tag}
                    type="button"
                    onClick={() => setTagFilter((prev) => (prev === tag ? null : tag))}
                    className={cn(
                      'inline-flex items-center rounded-full px-2 py-0.5 text-xs border transition-colors',
                      tagFilter === tag
                        ? 'bg-primary text-primary-foreground border-primary'
                        : 'border-border hover:bg-accent',
                    )}
                  >
                    #{tag}
                  </button>
                ))}
              </div>
            )}
            {activeFilters > 0 && (
              <button
                type="button"
                onClick={clearFilters}
                className="text-xs text-primary hover:underline"
              >
                Clear filters
              </button>
            )}
          </div>
        </CardContent>
      </Card>

      <ResultArea
        isLoading={isLoading}
        isError={isError}
        characters={characters}
        tagFilter={tagFilter}
        onClearTagFilter={() => setTagFilter(null)}
        onOpenDrawer={setSelected}
      />

      <CharacterDetailDrawer character={selected} onClose={() => setSelected(null)} />
    </div>
  )
}

function ResultArea({
  isLoading,
  isError,
  characters,
  tagFilter,
  onClearTagFilter,
  onOpenDrawer,
}: {
  isLoading: boolean
  isError: boolean
  characters: Character[]
  tagFilter: string | null
  onClearTagFilter: () => void
  onOpenDrawer: (c: Character) => void
}) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Card key={i} className="overflow-hidden">
            <div className="aspect-square w-full bg-muted animate-pulse" />
            <CardContent className="space-y-2 p-3">
              <div className="h-4 w-3/4 bg-muted rounded animate-pulse" />
              <div className="h-3 w-1/2 bg-muted rounded animate-pulse" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }
  if (isError) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 py-8 text-destructive">
          <AlertTriangle className="w-5 h-5" />
          <span>Failed to load characters. The Venice preview API may be unavailable.</span>
        </CardContent>
      </Card>
    )
  }
  if (characters.length === 0) {
    return (
      <Card>
        <CardContent className="text-center text-muted-foreground py-12 space-y-2">
          <p>No characters match your filters.</p>
          {tagFilter && (
            <button
              type="button"
              onClick={onClearTagFilter}
              className="text-primary text-sm hover:underline"
            >
              Clear tag filter
            </button>
          )}
        </CardContent>
      </Card>
    )
  }
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {characters.map((c) => (
        <CharacterCard
          key={c.id}
          character={c}
          onClick={onOpenDrawer}
        />
      ))}
    </div>
  )
}

function ToggleChip({
  active,
  onToggle,
  label,
  variant = 'default',
}: {
  active: boolean
  onToggle: () => void
  label: string
  variant?: 'default' | 'warning'
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={active}
      className={cn(
        'inline-flex items-center rounded-full border px-3 py-1 text-xs transition-colors',
        active
          ? variant === 'warning'
            ? 'border-warning bg-warning/10 text-warning'
            : 'border-primary bg-primary/10 text-primary'
          : 'border-border hover:bg-accent',
      )}
    >
      {label}
    </button>
  )
}
