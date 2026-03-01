import React from 'react'
import { render, screen } from '@testing-library/react'
import { UsageLeaderboardCard } from '@/components/dashboard/UsageLeaderboardCard'
import { useAPIKeysUsage } from '@/lib/hooks'

jest.mock('@/lib/hooks')
const mockUseAPIKeysUsage = useAPIKeysUsage as jest.MockedFunction<typeof useAPIKeysUsage>

const keysData = {
  keys: [
    { id: 'key_a', name: 'Main Key',  diem_usage: 50.25, usd_usage: 12.56, is_active: true  },
    { id: 'key_b', name: 'Dev Key',   diem_usage: 5.00,  usd_usage: 1.25,  is_active: false },
    { id: 'key_c', name: 'CI Key',    diem_usage: 20.00, usd_usage: 5.00,  is_active: true  },
  ],
}

describe('UsageLeaderboardCard — loading', () => {
  beforeEach(() => {
    mockUseAPIKeysUsage.mockReturnValue({ data: undefined, isLoading: true, isError: false } as any)
  })

  it('shows loading placeholder', () => {
    render(<UsageLeaderboardCard />)
    expect(screen.getByText(/loading usage data/i)).toBeInTheDocument()
  })
})

describe('UsageLeaderboardCard — error', () => {
  beforeEach(() => {
    mockUseAPIKeysUsage.mockReturnValue({ data: undefined, isLoading: false, isError: true } as any)
  })

  it('shows error message', () => {
    render(<UsageLeaderboardCard />)
    expect(screen.getByText(/failed to load usage data/i)).toBeInTheDocument()
  })
})

describe('UsageLeaderboardCard — success', () => {
  beforeEach(() => {
    mockUseAPIKeysUsage.mockReturnValue({ data: keysData, isLoading: false, isError: false } as any)
  })

  it('renders card title with trailing period info', () => {
    render(<UsageLeaderboardCard />)
    expect(screen.getByText(/API Key Usage \(7-Day Trailing\)/i)).toBeInTheDocument()
  })

  it('renders table headers', () => {
    render(<UsageLeaderboardCard />)
    expect(screen.getByText('Key Name')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('DIEM Usage')).toBeInTheDocument()
    expect(screen.getByText('USD Usage')).toBeInTheDocument()
  })

  it('renders all key names', () => {
    render(<UsageLeaderboardCard />)
    expect(screen.getByText('Main Key')).toBeInTheDocument()
    expect(screen.getByText('Dev Key')).toBeInTheDocument()
    expect(screen.getByText('CI Key')).toBeInTheDocument()
  })

  it('renders Active badge for active key', () => {
    render(<UsageLeaderboardCard />)
    const activeBadges = screen.getAllByText('Active')
    expect(activeBadges.length).toBeGreaterThanOrEqual(1)
  })

  it('renders Inactive badge for inactive key', () => {
    render(<UsageLeaderboardCard />)
    expect(screen.getByText('Inactive')).toBeInTheDocument()
  })

  it('sorts keys by DIEM usage descending (Main Key first)', () => {
    render(<UsageLeaderboardCard />)
    const rows = screen.getAllByRole('row')
    // rows[0] = header row, rows[1] = first data row (highest usage = Main Key)
    expect(rows[1]).toHaveTextContent('Main Key')
  })

  it('renders DIEM usage formatted to 4 decimals', () => {
    render(<UsageLeaderboardCard />)
    // formatNumber(50.25, 4) → "50.2500"
    expect(screen.getByText('50.2500')).toBeInTheDocument()
  })

  it('renders USD usage as currency', () => {
    render(<UsageLeaderboardCard />)
    // formatCurrency(12.56) → "$12.56"
    expect(screen.getByText('$12.56')).toBeInTheDocument()
  })

  it('shows empty state when no keys are returned', () => {
    mockUseAPIKeysUsage.mockReturnValue({
      data: { keys: [] },
      isLoading: false,
      isError: false,
    } as any)
    render(<UsageLeaderboardCard />)
    expect(screen.getByText(/no api keys found/i)).toBeInTheDocument()
  })
})
