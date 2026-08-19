'use client'

import { Star, Users, ExternalLink, AlertTriangle } from 'lucide-react'
import type { Character } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const MAX_TAGS_VISIBLE = 3

export interface CharacterCardProps {
  character: Character
  onClick?: (character: Character) => void
}

export function CharacterCard({ character, onClick }: CharacterCardProps) {
  const { stats, tags, name, slug, description, photoUrl, modelId, adult, featured, webEnabled } =
    character

  const tagsToShow = tags.slice(0, MAX_TAGS_VISIBLE)
  const moreTagCount = Math.max(0, tags.length - MAX_TAGS_VISIBLE)

  return (
    <Card
      className={cn(
        'group relative cursor-pointer overflow-hidden transition-colors hover:border-primary/60',
        onClick && 'hover:shadow-md',
      )}
      onClick={onClick ? () => onClick(character) : undefined}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onClick(character)
              }
            }
          : undefined
      }
      aria-label={`Open character ${name}`}
      data-slug={slug}
    >
      <div className="relative aspect-square w-full overflow-hidden bg-muted">
        {photoUrl ? (
          // eslint-disable-next-line @next/next/no-img-element -- Image is served by the same-origin API proxy.
          <img
            src={`/api/characters/${encodeURIComponent(slug)}/photo`}
            alt={name}
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-4xl font-medium text-muted-foreground">
            {name.slice(0, 1).toUpperCase()}
          </div>
        )}
        <div className="absolute top-2 right-2 flex gap-1">
          {adult && (
            <Badge variant="destructive" className="shadow-sm">
              18+
            </Badge>
          )}
          {featured && (
            <Badge variant="default" className="shadow-sm">
              Featured
            </Badge>
          )}
          {!webEnabled && (
            <Badge variant="secondary" className="shadow-sm">
              Web off
            </Badge>
          )}
        </div>
      </div>
      <CardContent className="space-y-2 p-3">
        <div>
          <h3 className="text-base font-semibold leading-tight truncate" title={name}>
            {name}
          </h3>
          <p className="text-xs text-muted-foreground truncate" title={`/${slug}`}>
            /{slug}
          </p>
        </div>
        {description && (
          <p className="line-clamp-2 text-xs text-muted-foreground">{description}</p>
        )}
        <div className="flex flex-wrap gap-1">
          {tagsToShow.map((tag) => (
            <Badge key={tag} variant="outline" className="text-xs">
              #{tag}
            </Badge>
          ))}
          {moreTagCount > 0 && (
            <Badge variant="outline" className="text-xs text-muted-foreground">
              +{moreTagCount}
            </Badge>
          )}
        </div>
        <div className="flex items-center justify-between pt-1 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1">
              <Star className="w-3 h-3 fill-warning text-warning" />
              {stats.averageRating.toFixed(1)}
            </span>
            <span className="flex items-center gap-1">
              <Users className="w-3 h-3" />
              {stats.imports}
            </span>
          </div>
          <span className="font-mono truncate" title={modelId}>
            {modelId}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}
