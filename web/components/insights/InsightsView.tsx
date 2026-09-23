'use client'

import { useState } from 'react'
import { api, type MarketAnalysis, type MarketDecisions, type DecisionAnswer, type DecisionsStatus } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui'
import { toast } from 'sonner'

// Sentiment score levels — must match backend _build_market_questions().
const SENTIMENT_LEVELS = [
  { key: '0', label: 'Bearish', color: 'bg-destructive' },
  { key: '1', label: 'Neutral', color: 'bg-amber-500' },
  { key: '2', label: 'Bullish', color: 'bg-emerald-500' },
]

function riskColor(value: number): string {
  if (value > 0.7) return 'text-destructive'
  if (value >= 0.4) return 'text-amber-500'
  return 'text-emerald-500'
}

function pct(value: number): string {
  return `${Math.round(value * 100)}%`
}

/** Stacked probability bar for the sentiment score distribution. */
function SentimentDistributionBar({ probabilities }: { probabilities: Record<string, number> }) {
  const entries = SENTIMENT_LEVELS.map((level) => ({ ...level, value: probabilities[level.key] ?? 0 }))
  const total = entries.reduce((sum, e) => sum + e.value, 0) || 1
  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted" role="img" aria-label="Sentiment probability distribution">
        {entries.map((e) => (
          <div key={e.key} className={e.color} style={{ width: `${(e.value / total) * 100}%` }} title={`${e.label} ${pct(e.value)}`} />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {entries.map((e) => (
          <span key={e.key} className="inline-flex items-center gap-1.5">
            <span className={`inline-block h-2 w-2 rounded-full ${e.color}`} aria-hidden />
            {e.label} <span className="font-medium text-foreground">{pct(e.value)}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

/** Highlighted choice plus small per-option probability bars. */
function PhaseOptionBars({ answer }: { answer: Extract<DecisionAnswer, { type: 'choice' }> }) {
  const options = Object.entries(answer.probabilities).sort((a, b) => b[1] - a[1])
  return (
    <div className="space-y-1.5">
      <p className="text-sm font-medium capitalize">{answer.choice}</p>
      {options.map(([option, value]) => (
        <div key={option} className="flex items-center gap-2 text-xs">
          <span className={`w-24 shrink-0 truncate capitalize ${option === answer.choice ? 'font-medium text-foreground' : 'text-muted-foreground'}`}>{option}</span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
            <div className={`h-full rounded-full ${option === answer.choice ? 'bg-primary' : 'bg-muted-foreground/40'}`} style={{ width: `${value * 100}%` }} />
          </div>
          <span className="w-8 shrink-0 text-right tabular-nums text-muted-foreground">{pct(value)}</span>
        </div>
      ))}
    </div>
  )
}

/** One compact tile per typed question inside the judgments card. */
function JudgmentTile({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border bg-card/50 p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</p>
      {children}
    </div>
  )
}

/** Renders the four typed Jev judgments. Shown only when decisions exist. */
function TypedJudgmentsCard({ decisions }: { decisions: MarketDecisions }) {
  const sentiment = decisions.answers.sentiment
  const risk = decisions.answers.is_high_risk
  const phase = decisions.answers.market_phase
  const news = decisions.answers.news_supports_bullish

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-3">
          Typed Judgments
          <Badge variant="secondary" className="font-normal text-xs">Jev · Anonymized · beta</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-2">
          {sentiment?.type === 'score' && (
            <JudgmentTile title="Sentiment">
              <p className="mb-3 text-2xl font-bold">
                {sentiment.legend[String(Math.round(sentiment.score))] ?? '—'}
                <span className="ml-2 text-sm font-normal text-muted-foreground">score {sentiment.score.toFixed(2)}</span>
              </p>
              <SentimentDistributionBar probabilities={sentiment.probabilities} />
              <p className="mt-3 text-xs text-muted-foreground">Confidence {pct(sentiment.confidence)}</p>
            </JudgmentTile>
          )}
          {risk?.type === 'noul' && (
            <JudgmentTile title="Downside risk">
              <p className={`text-4xl font-bold tabular-nums ${riskColor(risk.noul)}`}>{pct(risk.noul)}</p>
              <p className="mt-2 text-xs text-muted-foreground">Probability the current state implies elevated downside risk for VVV/DIEM holders. Lower is better.</p>
            </JudgmentTile>
          )}
          {phase?.type === 'choice' && (
            <JudgmentTile title="Market phase">
              <PhaseOptionBars answer={phase} />
              <p className="mt-3 text-xs text-muted-foreground">Confidence {pct(phase.confidence)}</p>
            </JudgmentTile>
          )}
          {news?.type === 'noul' && (
            <JudgmentTile title="News check">
              <p className="text-4xl font-bold tabular-nums text-foreground">{pct(news.noul)}</p>
              <p className="mt-2 text-xs text-muted-foreground">
                Probability that current news supports a bullish outlook — {news.noul >= 0.5 ? 'supportive' : 'not supportive'}.
              </p>
            </JudgmentTile>
          )}
        </div>
        <p className="mt-4 text-xs text-muted-foreground">
          Independent machine judgments of the same state as the briefing ({decisions.usage.input_tokens} in / {decisions.usage.output_tokens} out tokens). They may disagree with the prose analysis.
        </p>
      </CardContent>
    </Card>
  )
}

export function InsightsView() {
  const [analysis, setAnalysis] = useState<MarketAnalysis | null>(null)
  const [decisions, setDecisions] = useState<MarketDecisions | null>(null)
  const [decisionsStatus, setDecisionsStatus] = useState<DecisionsStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.analyzeMarket()
      setAnalysis(result.analysis)
      setDecisions(result.decisions ?? null)
      setDecisionsStatus(result.decisions_status ?? (result.decisions ? 'ok' : 'unavailable'))
      toast.success('Market analysis generated')
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Analysis failed'
      setError(message)
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">AI Market Insights</h1>
          <p className="text-sm text-muted-foreground mt-1">A contextual briefing, not financial advice</p>
        </div>
        <Button onClick={run} disabled={loading}>
          {loading ? 'Analyzing…' : 'Generate analysis'}
        </Button>
      </div>
      {error && <p className="text-destructive" role="alert">{error}</p>}
      {analysis && (
        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-3">
                Briefing
                <Badge variant={analysis.sentiment === 'bullish' ? 'success' : analysis.sentiment === 'bearish' ? 'destructive' : 'secondary'}>{analysis.sentiment}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="leading-7">{analysis.summary}</p>
              <h2 className="mt-6 font-semibold">Key events</h2>
              <ul className="mt-2 list-disc pl-5 text-sm space-y-1">
                {analysis.key_events?.map((event) => <li key={event}>{event}</li>)}
              </ul>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Confidence</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-4xl font-bold">{analysis.confidence}%</p>
              <div className="mt-3 h-2 rounded-full bg-muted">
                <div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(100, Math.max(0, analysis.confidence))}%` }} />
              </div>
              <h2 className="mt-6 font-semibold">Risks</h2>
              <ul className="mt-2 list-disc pl-5 text-sm space-y-1">
                {analysis.risks?.map((risk) => <li key={risk}>{risk}</li>)}
              </ul>
            </CardContent>
          </Card>
        </div>
      )}
      {analysis && decisions && <TypedJudgmentsCard decisions={decisions} />}
      {analysis && !decisions && decisionsStatus === 'unavailable' && (
        <p className="text-xs text-muted-foreground">
          Typed judgments unavailable — Venice's beta decision model didn't respond. The briefing above is unaffected.
        </p>
      )}
    </div>
  )
}
