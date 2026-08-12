'use client'

import { Star, Users, ExternalLink, Cpu } from 'lucide-react'
import type { Character } from '@/lib/api'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui'
import { cn } from '@/lib/utils'

export interface CharacterDetailDrawerProps {
  character: Character | null
  onClose: () => void
}

export function CharacterDetailDrawer({ character, onClose }: CharacterDetailDrawerProps) {
  if (!character) return null

  const {
    name,
    slug,
    description,
    tags,
    photoUrl,
    modelId,
    shareUrl,
    adult,
    featured,
    webEnabled,
    author,
    createdAt,
    updatedAt,
    stats,
  } = character

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        aria-labelledby="character-drawer-title"
        closeLabel="Close drawer"
        className="left-auto right-0 top-0 h-full max-h-full w-full max-w-lg translate-x-0 translate-y-0 rounded-none border-y-0 border-r-0 p-0"
        onClick={(event) => {
          if (event.target === event.currentTarget) onClose()
        }}
      >
        <div className="h-full overflow-y-auto">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-card/95 backdrop-blur-sm p-4">
          <DialogTitle id="character-drawer-title" className="truncate text-lg font-semibold">
            {name}
          </DialogTitle>
        </div>

        {photoUrl && (
          <div className="aspect-square w-full overflow-hidden bg-muted">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={photoUrl}
              alt={name}
              className="h-full w-full object-cover"
              referrerPolicy="no-referrer"
            />
          </div>
        )}

        <div className="space-y-6 p-4">
          <div className="flex flex-wrap gap-2">
            {adult && <Badge variant="destructive">Adult (18+)</Badge>}
            {featured && <Badge>Featured</Badge>}
            <Badge variant={webEnabled ? 'success' : 'secondary'}>
              {webEnabled ? 'Web enabled' : 'Web disabled'}
            </Badge>
          </div>

          <section>
            <h3 className="text-xs font-medium text-muted-foreground mb-1">Description</h3>
            <p className="text-sm leading-relaxed">
              {description ?? <span className="italic text-muted-foreground">No description.</span>}
            </p>
          </section>

          {tags.length > 0 && (
            <section>
              <h3 className="text-xs font-medium text-muted-foreground mb-2">Tags</h3>
              <div className="flex flex-wrap gap-1">
                {tags.map((t) => (
                  <Badge key={t} variant="outline">
                    #{t}
                  </Badge>
                ))}
              </div>
            </section>
          )}

          <section className="grid grid-cols-3 gap-3 rounded-lg border border-border p-3">
            <Stat label="Avg rating" value={stats.averageRating.toFixed(1)} icon={Star} />
            <Stat label="Imports" value={String(stats.imports)} icon={Users} />
            <Stat label="Ratings" value={String(stats.ratingCount)} icon={Star} />
          </section>

          <section>
            <h3 className="text-xs font-medium text-muted-foreground mb-1">Model</h3>
            <div className="flex items-center gap-2 text-sm">
              <Cpu className="w-4 h-4 text-muted-foreground" />
              <code className="rounded bg-muted px-1.5 py-0.5 text-xs">{modelId}</code>
            </div>
          </section>

          <section>
            <h3 className="text-xs font-medium text-muted-foreground mb-1">Slug</h3>
            <code className="rounded bg-muted px-1.5 py-0.5 text-xs">/{slug}</code>
          </section>

          <section>
            <h3 className="text-xs font-medium text-muted-foreground mb-1">Author</h3>
            <p className="text-sm font-mono">{author}</p>
          </section>

          <section className="grid grid-cols-2 gap-3 text-xs text-muted-foreground">
            <div>
              <span className="font-medium text-foreground">Created:</span>{' '}
              {new Date(createdAt).toLocaleDateString()}
            </div>
            <div>
              <span className="font-medium text-foreground">Updated:</span>{' '}
              {new Date(updatedAt).toLocaleDateString()}
            </div>
          </section>

          {shareUrl && (
            <a
              href={shareUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                'inline-flex h-10 items-center gap-1.5 rounded-md border border-input px-4 py-2 text-sm font-medium hover:bg-accent',
              )}
            >
              <ExternalLink className="w-4 h-4" />
              Open on Venice
            </a>
          )}
        </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function Stat({
  label,
  value,
  icon: Icon,
}: {
  label: string
  value: string
  icon: React.ComponentType<{ className?: string }>
}) {
  return (
    <div className="flex flex-col items-start">
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        <Icon className="w-3 h-3" />
        {label}
      </div>
      <span className="text-lg font-semibold leading-none">{value}</span>
    </div>
  )
}
