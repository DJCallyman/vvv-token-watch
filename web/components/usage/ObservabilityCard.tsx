'use client'

import { useObservabilitySummary, useRpcCosts } from '@/lib/hooks'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { DataState } from '@/components/ui/data-state'
import { Badge } from '@/components/ui/badge'
import { formatDateTime } from '@/lib/utils'
import { useDisplayPreferences } from '@/components/PreferencesProvider'
import { Activity, Gauge, ShieldCheck } from 'lucide-react'

function Availability({ status, reason, note }: { status?: string; reason?: string; note?: string }) {
  if (status === 'ok' || status === 'confirmed') {
    return <Badge variant="success">Available</Badge>
  }
  if (status === 'unverified') {
    return (
      <span className="inline-flex flex-col gap-1">
        <Badge variant="secondary">Unverified</Badge>
        {(note || reason) && (
          <span className="text-xs text-muted-foreground">{note ?? reason}</span>
        )}
      </span>
    )
  }
  return (
    <span className="inline-flex flex-col gap-1">
      <Badge variant="secondary">Unavailable</Badge>
      {(note || reason) && (
        <span className="text-xs text-muted-foreground">{note ?? reason}</span>
      )}
    </span>
  )
}

export function ObservabilityCard() {
  const { timezone } = useDisplayPreferences()
  const { data, isLoading, isError, refetch } = useObservabilitySummary()
  const { data: costs } = useRpcCosts()

  const rpc = data?.rpc_costs
  const rateHeaders = data?.rate_limits
  const events = data?.upstream_events
  const coverage = costs?.billing_coverage

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Gauge className="w-5 h-5" aria-hidden="true" />
          Rate Limits &amp; RPC Costs
        </CardTitle>
        <CardDescription>
          Upstream Venice telemetry (from authoritative response headers), kept separate
          from this app&apos;s own request limiter. Missing data is never shown as zero.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {isLoading && <DataState kind="loading" title="Loading telemetry" rows={3} />}
        {isError && !data && (
          <DataState
            kind="error"
            title="Could not load telemetry"
            description="Upstream telemetry may be temporarily unavailable."
            onRetry={() => { void refetch() }}
          />
        )}
        {data && (
          <>
            <div className="rounded-md border border-border p-4">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-muted-foreground" aria-hidden="true" />
                <p className="text-sm font-medium">This app&apos;s request limiter</p>
                <Badge variant="success">Active</Badge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {data.rate_limits.reason === 'no_rate_limit_headers_observed'
                  ? 'No upstream response has reported rate-limit headers yet.'
                  : 'Distinct from upstream Venice limits.'}
              </p>
            </div>

            <div className="rounded-md border border-border p-4 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium">Upstream rate-limit headers</p>
                <Availability status={rateHeaders?.status} reason={rateHeaders?.reason} note={rateHeaders?.note} />
              </div>
              {rateHeaders?.fields && (
                <ul className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
                  {Object.entries(rateHeaders.fields).map(([key, field]) => (
                    <li key={key} className="rounded bg-muted/50 p-2">
                      <p className="truncate font-mono text-[11px] text-muted-foreground">{key}</p>
                      <p className="font-semibold">{field.value}</p>
                    </li>
                  ))}
                </ul>
              )}
              {rateHeaders?.last_seen_at && (
                <p className="text-xs text-muted-foreground">
                  Last observed {formatDateTime(rateHeaders.last_seen_at, timezone)}
                </p>
              )}
            </div>

            <div className="rounded-md border border-border p-4 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium">Venice rate-limit events (ADMIN only)</p>
                <Availability status={events?.status} reason={events?.reason} note={events?.note} />
              </div>
              {events?.status === 'ok' && (
                <p className="text-xs text-muted-foreground">
                  {events.count ?? 0} exceeded-limit event(s) reported by the experimental
                  upstream log.
                </p>
              )}
              {events?.reason === 'forbidden_admin_key_required' && (
                <p className="text-xs text-muted-foreground">
                  The configured key is not an ADMIN key, so this telemetry is unavailable.
                </p>
              )}
            </div>

            <div className="rounded-md border border-border p-4 space-y-2">
              <div className="flex items-center justify-between gap-2">
                <p className="flex items-center gap-2 text-sm font-medium">
                  <Activity className="w-4 h-4" aria-hidden="true" />
                  Crypto RPC costs (per call)
                </p>
                <Availability status={rpc?.status} reason={rpc?.reason} note={rpc?.note} />
              </div>
              {rpc?.status === 'ok' && rpc.totals && (
                <div className="grid grid-cols-3 gap-2 text-sm">
                  <div className="rounded bg-muted/50 p-2">
                    <p className="text-xs text-muted-foreground">Total USD</p>
                    <p className="font-semibold">${rpc.totals.cost_usd.toFixed(4)}</p>
                  </div>
                  <div className="rounded bg-muted/50 p-2">
                    <p className="text-xs text-muted-foreground">Total credits</p>
                    <p className="font-semibold">{rpc.totals.credits.toFixed(2)}</p>
                  </div>
                  <div className="rounded bg-muted/50 p-2">
                    <p className="text-xs text-muted-foreground">Samples</p>
                    <p className="font-semibold">{rpc.totals.count}</p>
                  </div>
                </div>
              )}
              <p className="text-xs text-muted-foreground">
                {rpc?.source ?? 'Read from X-Venice-RPC-Cost-USD response headers.'} Costs are
                never estimated from call counts.
              </p>
            </div>

            <div className="rounded-md border border-border p-4 space-y-1">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium">Billing ledger coverage</p>
                <Availability
                  status={coverage?.status}
                  reason={coverage?.reason}
                  note={coverage?.note}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                {coverage?.note ??
                  'Billing reconciliation is used only when RPC charges are confirmed in the ledger.'}
              </p>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
