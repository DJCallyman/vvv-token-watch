'use client'

import { useState } from 'react'
import { api, type MarketAnalysis } from '@/lib/api'
import { useAnalyzeXSentiment, useBriefing, useMarketInfographic, useVideoRecapStatus } from '@/lib/hooks'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'
import { Image as ImageIcon, Play, Radio, Sparkles, Video } from 'lucide-react'

export function AiToolsPanel({ analysis }: { analysis: MarketAnalysis | null }) {
  const sentiment = useAnalyzeXSentiment()
  const infographic = useMarketInfographic()
  const briefing = useBriefing()
  const [queueId, setQueueId] = useState<string | null>(null)
  const [queueModel, setQueueModel] = useState<string | undefined>(undefined)
  const [queueing, setQueueing] = useState(false)

  const video = useVideoRecapStatus(queueId, queueModel)

  const queueRecap = async () => {
    setQueueing(true)
    try {
      const result = await api.queueVideoRecap()
      setQueueId(result.queue_id)
      setQueueModel(result.model)
      toast.success('Video recap queued')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to queue video recap')
    } finally {
      setQueueing(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="w-5 h-5" aria-hidden="true" />
          AI Analysis Tools
        </CardTitle>
        <CardDescription>
          X sentiment, infographics, spoken briefings, and video recaps via Venice models.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            onClick={() => sentiment.mutate(undefined)}
            disabled={sentiment.isPending}
          >
            <Radio className="w-4 h-4" aria-hidden="true" />
            {sentiment.isPending ? 'Analyzing X…' : 'Analyze X sentiment'}
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              infographic.mutate({
                summary: analysis?.summary,
                direction: (analysis?.sentiment as 'bullish' | 'bearish' | 'neutral') ?? 'neutral',
                confidence: analysis?.confidence,
                key_points: analysis?.key_events,
              })
            }
            disabled={infographic.isPending}
          >
            <ImageIcon className="w-4 h-4" aria-hidden="true" />
            {infographic.isPending ? 'Generating…' : 'Generate infographic'}
          </Button>
          <Button onClick={() => briefing.mutate(undefined)} disabled={briefing.isPending}>
            <Play className="w-4 h-4" aria-hidden="true" />
            {briefing.isPending ? 'Generating…' : 'Daily briefing'}
          </Button>
          <Button variant="outline" onClick={() => { void queueRecap() }} disabled={queueing}>
            <Video className="w-4 h-4" aria-hidden="true" />
            {queueing ? 'Queueing…' : 'Video recap'}
          </Button>
        </div>

        {sentiment.data && (
          <div className="rounded-md border border-border p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant={
                  sentiment.data.direction === 'bullish'
                    ? 'success'
                    : sentiment.data.direction === 'bearish'
                      ? 'destructive'
                      : 'secondary'
                }
              >
                {sentiment.data.direction}
              </Badge>
              <span className="text-sm font-medium">
                {sentiment.data.confidence.toFixed(0)}% confidence
              </span>
              <span className="text-xs text-muted-foreground">
                {sentiment.data.posts.length} post(s)
              </span>
            </div>
            <p className="mt-2 text-sm">{sentiment.data.summary}</p>
            <p className="mt-2 text-xs text-muted-foreground">{sentiment.data.note}</p>
          </div>
        )}

        {infographic.isPending && (
          <Skeleton className="h-64 w-full" aria-label="Generating infographic" />
        )}
        {infographic.data && (
          <figure className="space-y-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`data:image/png;base64,${infographic.data.image_b64}`}
              alt="AI-generated VVV/DIEM market infographic"
              className="w-full rounded-md border border-border"
            />
            <figcaption className="text-xs text-muted-foreground">
              AI-generated infographic from {infographic.data.signal_count} tracked signal(s).
              Informational only.
            </figcaption>
          </figure>
        )}

        {briefing.data && (
          <div className="rounded-md border border-border p-4 space-y-2">
            <p className="text-sm">{briefing.data.text}</p>
            <audio
              controls
              src={`data:${briefing.data.mime};base64,${briefing.data.audio_b64}`}
              className="w-full"
            >
              Your browser does not support audio playback.
            </audio>
          </div>
        )}

        {queueId && (
          <div className="rounded-md border border-border p-4 space-y-2">
            <p className="text-sm font-medium">
              Video recap status: {video.data?.status ?? 'queued'}
            </p>
            {video.data?.video_url && (
              <video controls src={video.data.video_url} className="w-full rounded-md">
                Your browser does not support video playback.
              </video>
            )}
            {video.data?.status !== 'completed' && video.data?.status !== 'error' && (
              <p className="text-xs text-muted-foreground">
                Video generation is asynchronous; this panel refreshes automatically.
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
