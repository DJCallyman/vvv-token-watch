'use client'

import { useState } from 'react'
import { api, type MarketAnalysis } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui'
import { toast } from 'sonner'

export function InsightsView() {
  const [analysis, setAnalysis] = useState<MarketAnalysis | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
   const run = async () => { setLoading(true); setError(null); try { setAnalysis((await api.analyzeMarket()).analysis); toast.success('Market analysis generated') } catch (e) { const message = e instanceof Error ? e.message : 'Analysis failed'; setError(message); toast.error(message) } finally { setLoading(false) } }
   return <div className="space-y-6"><div className="flex items-center justify-between"><div><h1 className="text-3xl font-bold">AI Market Insights</h1><p className="text-sm text-muted-foreground mt-1">A contextual briefing, not financial advice</p></div><Button onClick={run} disabled={loading}>{loading ? 'Analyzing…' : 'Generate analysis'}</Button></div>{error && <p className="text-destructive" role="alert">{error}</p>}{analysis && <div className="grid gap-6 lg:grid-cols-3"><Card className="lg:col-span-2"><CardHeader><CardTitle className="flex items-center gap-3">Briefing <Badge variant={analysis.sentiment === 'bullish' ? 'success' : analysis.sentiment === 'bearish' ? 'destructive' : 'secondary'}>{analysis.sentiment}</Badge></CardTitle></CardHeader><CardContent><p className="leading-7">{analysis.summary}</p><h2 className="mt-6 font-semibold">Key events</h2><ul className="mt-2 list-disc pl-5 text-sm space-y-1">{analysis.key_events?.map((event) => <li key={event}>{event}</li>)}</ul></CardContent></Card><Card><CardHeader><CardTitle>Confidence</CardTitle></CardHeader><CardContent><p className="text-4xl font-bold">{analysis.confidence}%</p><div className="mt-3 h-2 rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${Math.min(100, Math.max(0, analysis.confidence))}%` }} /></div><h2 className="mt-6 font-semibold">Risks</h2><ul className="mt-2 list-disc pl-5 text-sm space-y-1">{analysis.risks?.map((risk) => <li key={risk}>{risk}</li>)}</ul></CardContent></Card></div>}</div>
}
