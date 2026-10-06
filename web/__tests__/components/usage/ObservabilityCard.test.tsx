import { render, screen } from '../../test-utils'
import { ObservabilityCard } from '@/components/usage/ObservabilityCard'
import { useObservabilitySummary, useRpcCosts } from '@/lib/hooks'

jest.mock('@/lib/hooks')

const mockUseSummary = useObservabilitySummary as jest.MockedFunction<typeof useObservabilitySummary>
const mockUseRpcCosts = useRpcCosts as jest.MockedFunction<typeof useRpcCosts>

beforeEach(() => {
  jest.clearAllMocks()
})

describe('ObservabilityCard', () => {
  it('shows unavailable states with reasons instead of zeros', () => {
    mockUseSummary.mockReturnValue({
      data: {
        headers: { status: 'unavailable', reason: 'no_venice_headers_observed' },
        rate_limits: {
          status: 'unavailable',
          reason: 'no_rate_limit_headers_observed',
          note: 'No Venice response has reported rate-limit headers yet.',
        },
        rpc_costs: { status: 'unavailable', reason: 'no_rpc_cost_headers_observed' },
        upstream_events: { status: 'unavailable', reason: 'forbidden_admin_key_required' },
        generated_at: '2026-01-01T00:00:00Z',
      },
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    } as any)
    mockUseRpcCosts.mockReturnValue({
      data: {
        per_call: { status: 'unavailable', reason: 'no_rpc_cost_headers_observed' },
        billing_coverage: {
          status: 'unverified',
          scanned: 100,
          rpc_entries: 0,
          note: 'No RPC charges were found in the sampled billing page.',
        },
        account_reconciliation: { status: 'unverified', note: 'x' },
      },
      isLoading: false,
      isError: false,
    } as any)

    render(<ObservabilityCard />)
    expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Unverified').length).toBeGreaterThan(0)
    expect(screen.getByText(/No Venice response has reported rate-limit headers yet/i)).toBeInTheDocument()
    expect(screen.getAllByText(/No RPC charges were found/i).length).toBeGreaterThan(0)
    // No fabricated zero totals when telemetry is missing.
    expect(screen.queryByText('$0.0000')).not.toBeInTheDocument()
  })

  it('reports available header and cost telemetry with freshness', () => {
    mockUseSummary.mockReturnValue({
      data: {
        headers: { status: 'ok', last_seen_at: '2026-01-01T00:00:00Z' },
        rate_limits: {
          status: 'ok',
          fields: { 'x-ratelimit-limit': { value: '60', endpoint: '/x', timestamp: '2026-01-01T00:00:00Z' } },
          last_seen_at: '2026-01-01T00:00:00Z',
        },
        rpc_costs: {
          status: 'ok',
          totals: { cost_usd: 0.0025, credits: 5, count: 2 },
          latest: { cost_usd: 0.0025, credits: 5 },
          sample_count: 2,
          source: 'X-Venice-RPC headers',
        },
        upstream_events: { status: 'ok', events: [], count: 0 },
        generated_at: '2026-01-01T00:00:00Z',
      },
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    } as any)
    mockUseRpcCosts.mockReturnValue({
      data: {
        per_call: { status: 'ok' },
        billing_coverage: { status: 'confirmed', scanned: 100, rpc_entries: 3, note: 'RPC charges appear.' },
        account_reconciliation: { status: 'available', note: 'x' },
      },
      isLoading: false,
      isError: false,
    } as any)

    render(<ObservabilityCard />)
    expect(screen.getByText('x-ratelimit-limit')).toBeInTheDocument()
    expect(screen.getByText('60')).toBeInTheDocument()
    expect(screen.getByText('$0.0025')).toBeInTheDocument()
    expect(screen.getByText(/RPC charges appear/i)).toBeInTheDocument()
  })
})
