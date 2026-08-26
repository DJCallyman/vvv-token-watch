import React from 'react'
import { render, screen } from '../../test-utils'
import { ModelAnalytics } from '@/components/models/ModelAnalytics'
import { useAnalytics, useDailyAnalytics } from '@/hooks/useAnalytics'

jest.mock('@/hooks/useAnalytics')
jest.mock('recharts', () => {
  const Passthrough = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>
  const Empty = () => null
  return {
    BarChart: Passthrough,
    Bar: Empty,
    XAxis: Empty,
    YAxis: Empty,
    CartesianGrid: Empty,
    Tooltip: Empty,
    ResponsiveContainer: Passthrough,
    PieChart: Passthrough,
    Pie: Passthrough,
    Cell: Empty,
    LineChart: Passthrough,
    Line: Empty,
    Legend: Empty,
  }
})

const mockUseAnalytics = useAnalytics as jest.MockedFunction<typeof useAnalytics>
const mockUseDailyAnalytics = useDailyAnalytics as jest.MockedFunction<typeof useDailyAnalytics>

beforeEach(() => {
  mockUseAnalytics.mockReturnValue({
    data: {
      model_usage: {
        'elevenlabs-music': {
          requests: null,
          tokens: 100,
          prompt_tokens: 60,
          completion_tokens: 40,
          cost: 5.7978,
          cost_usd: 1.23,
          cost_diem: 4.5678,
          cost_bundled_credits: 0,
          avg_response_time_ms: null,
          model_type: 'music',
          breakdown: [
            { type: 'Input', usd: 1.23, diem: 4.5678, units: 60 },
            { type: 'Output', usd: 0, diem: 1.23, units: 40 },
          ],
        },
      },
      total_requests: 0,
      total_tokens: 100,
      total_cost: 5.7978,
      period_days: 7,
      recommendations: [],
      source: 'billing/usage-analytics',
    },
    isLoading: false,
    isError: false,
  } as any)
  mockUseDailyAnalytics.mockReturnValue({
    data: { daily_usage: [], period_days: 7, source: 'billing/usage-analytics' },
    isLoading: false,
    isError: false,
  } as any)
})

describe('ModelAnalytics', () => {
  it('renders music filters and keeps currency breakdowns separate', () => {
    render(<ModelAnalytics />)

    expect(screen.getByRole('option', { name: 'Music' })).toBeInTheDocument()
    expect(screen.getByText('Cost Summary')).toBeInTheDocument()
    expect(screen.getAllByText('$1.23')).toHaveLength(2)
    expect(screen.getAllByText('4.5678 DIEM')).toHaveLength(2)
    expect(screen.getByText('Cost Breakdown')).toBeInTheDocument()
    expect(screen.getByText('Input').parentElement).toHaveTextContent('$1.23')
    expect(screen.getByText('Output').parentElement).toHaveTextContent('1.2300 DIEM')
  })

  it('removes unavailable request and latency columns for aggregated analytics', () => {
    mockUseAnalytics.mockReturnValue({
      data: {
        model_usage: {
          'test-model': {
            requests: null,
            tokens: 100,
            prompt_tokens: 60,
            completion_tokens: 40,
            cost: 2,
            cost_usd: 0,
            cost_diem: 2,
            avg_response_time_ms: null,
            model_type: 'llm',
          },
        },
        total_requests: 0,
        total_tokens: 100,
        total_cost: 2,
        period_days: 7,
        recommendations: [],
        source: 'billing/usage-analytics',
      },
      isLoading: false,
      isError: false,
    } as any)
    mockUseDailyAnalytics.mockReturnValue({
      data: {
        daily_usage: [{ date: '2026-08-18', requests: null, tokens: null, cost: 2, cost_usd: 0, cost_diem: 2 }],
        period_days: 7,
        source: 'billing/usage-analytics',
      },
      isLoading: false,
      isError: false,
    } as any)

    render(<ModelAnalytics />)

    expect(screen.getByText('—')).toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: 'Requests' })).not.toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: 'Avg Latency' })).not.toBeInTheDocument()
  })

  it('keeps model analytics visible when the daily query fails', () => {
    mockUseDailyAnalytics.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error('daily unavailable'),
    } as any)

    render(<ModelAnalytics />)

    expect(screen.getByText('Model Analytics')).toBeInTheDocument()
    expect(screen.getByText('Daily trend data is unavailable.')).toBeInTheDocument()
  })
})
