import React from 'react'
import { render, screen } from '../../test-utils'
import { Header } from '@/components/layout/Header'
import {
  useBalance,
  useResetSettings,
  useSettings,
  useUnacknowledgedAlertEvents,
  useUpdateSettings,
} from '@/lib/hooks'

jest.mock('@/lib/hooks')
const mockUseBalance = useBalance as jest.MockedFunction<typeof useBalance>
const mockUseUnacknowledgedAlertEvents = useUnacknowledgedAlertEvents as jest.MockedFunction<typeof useUnacknowledgedAlertEvents>
const mockUseSettings = useSettings as jest.MockedFunction<typeof useSettings>
const mockUseUpdateSettings = useUpdateSettings as jest.MockedFunction<typeof useUpdateSettings>
const mockUseResetSettings = useResetSettings as jest.MockedFunction<typeof useResetSettings>

const balanceData = {
  diem: 45.5,
  usd: 11.25,
  daily_diem_limit: 100.0,
  daily_usd_limit: 25.0,
  diem_usage_percent: 45.5,
  usd_usage_percent: 45.0,
  next_epoch_begins: '2026-03-02T00:00:00Z',
}

const settingsData = {
  coingecko_token_id: 'venice-token',
  coingecko_currencies: ['usd', 'aud'],
  coingecko_holding_amount: 2750,
  diem_token_id: 'diem',
  diem_holding_amount: 0,
  benchmark_max_cost_usd: 5,
  benchmark_enable_billing_reconciliation: false,
  benchmark_judge_model: 'zai-org-glm-5-2',
}

function mockSettingsHooks() {
  mockUseSettings.mockReturnValue({ data: settingsData, isLoading: false } as any)
  mockUseUpdateSettings.mockReturnValue({ mutate: jest.fn(), isPending: false } as any)
  mockUseResetSettings.mockReturnValue({ mutate: jest.fn(), isPending: false } as any)
}

describe('Header — loading', () => {
  beforeEach(() => {
    mockSettingsHooks()
    mockUseBalance.mockReturnValue({ data: undefined, isLoading: true, isError: false } as any)
    mockUseUnacknowledgedAlertEvents.mockReturnValue({ data: undefined, isLoading: false, isError: false } as any)
  })

  it('renders without crashing while loading', () => {
    render(<Header />)
    // The spinner (RefreshCw) should be visible during loading
    const header = screen.getByRole('banner')
    expect(header).toBeInTheDocument()
  })

  it('renders Connecting badge while loading (not yet errored)', () => {
    render(<Header />)
    expect(screen.getByText('Connecting')).toBeInTheDocument()
  })

  it('does not show balance values while loading', () => {
    render(<Header />)
    expect(screen.queryByText('DIEM Balance')).not.toBeInTheDocument()
  })
})

describe('Header — error', () => {
  beforeEach(() => {
    mockSettingsHooks()
    mockUseBalance.mockReturnValue({ data: undefined, isLoading: false, isError: true } as any)
    mockUseUnacknowledgedAlertEvents.mockReturnValue({ data: undefined, isLoading: false, isError: false } as any)
  })

  it('renders Disconnected badge on error', () => {
    render(<Header />)
    expect(screen.getByText('Disconnected')).toBeInTheDocument()
  })

  it('does not show balance values on error', () => {
    render(<Header />)
    expect(screen.queryByText('DIEM Balance')).not.toBeInTheDocument()
  })
})

describe('Header — success', () => {
  beforeEach(() => {
    mockSettingsHooks()
    mockUseBalance.mockReturnValue({ data: balanceData, isLoading: false, isError: false } as any)
    mockUseUnacknowledgedAlertEvents.mockReturnValue({ data: { count: 0 }, isLoading: false, isError: false } as any)
  })

  it('renders Connected badge', () => {
    render(<Header />)
    expect(screen.getByText('Connected')).toBeInTheDocument()
  })

  it('renders DIEM Balance label', () => {
    render(<Header />)
    expect(screen.getByText('DIEM Balance')).toBeInTheDocument()
  })

  it('renders DIEM numeric balance', () => {
    render(<Header />)
    // formatNumber(45.5, 4) → "45.5000"
    expect(screen.getByText('45.5000')).toBeInTheDocument()
  })

  it('renders USD Balance label', () => {
    render(<Header />)
    expect(screen.getByText('USD Balance')).toBeInTheDocument()
  })

  it('renders USD currency balance', () => {
    render(<Header />)
    // formatCurrency(11.25) → "$11.25"
    expect(screen.getByText('$11.25')).toBeInTheDocument()
  })
})
