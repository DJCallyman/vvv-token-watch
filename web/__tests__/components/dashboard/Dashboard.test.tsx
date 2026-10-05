import { fireEvent, render, screen, waitFor } from '../../test-utils'
import { Dashboard } from '@/components/dashboard/Dashboard'
import { useSettings, useUpdateSettings } from '@/lib/hooks'

jest.mock('@/components/dashboard/HeroBalanceCard', () => ({
  HeroBalanceCard: () => <div>Balance widget</div>,
}))
jest.mock('@/components/dashboard/TodayUsageCard', () => ({
  TodayUsageCard: () => <div>Usage widget</div>,
}))
jest.mock('@/components/dashboard/PriceCards', () => ({
  PriceCards: () => <div>Prices widget</div>,
}))
jest.mock('@/components/dashboard/UsageLeaderboardCard', () => ({
  UsageLeaderboardCard: () => <div>API keys widget</div>,
}))
jest.mock('@/lib/hooks')

const mockUseSettings = useSettings as jest.MockedFunction<typeof useSettings>
const mockUseUpdateSettings = useUpdateSettings as jest.MockedFunction<typeof useUpdateSettings>

const defaultSettings = {
  dashboard_layout: ['balance', 'usage', 'prices', 'usage_leaderboard'],
}

describe('Dashboard layout preferences', () => {
  const mutateAsync = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    mutateAsync.mockResolvedValue(defaultSettings)
    mockUseSettings.mockReturnValue({ data: defaultSettings, isLoading: false } as any)
    mockUseUpdateSettings.mockReturnValue({ mutateAsync, isPending: false } as any)
  })

  it('saves widget order when the accessible move control is used', async () => {
    render(<Dashboard />)

    fireEvent.click(screen.getByRole('button', { name: 'Move Token prices up' }))

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        dashboard_layout: ['balance', 'prices', 'usage', 'usage_leaderboard'],
      })
    })
  })

  it('persists the default layout when reset is selected', async () => {
    mockUseSettings.mockReturnValue({
      data: {
        dashboard_layout: ['prices', 'balance', 'usage', 'usage_leaderboard'],
      },
      isLoading: false,
    } as any)

    render(<Dashboard />)
    fireEvent.click(screen.getByRole('button', { name: 'Reset layout' }))

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        dashboard_layout: ['balance', 'usage', 'prices', 'usage_leaderboard'],
      })
    })
  })

  it('supports drag-and-drop reordering', async () => {
    render(<Dashboard />)
    const items = screen.getAllByRole('listitem')
    const prices = items.find((item) => item.getAttribute('data-widget-id') === 'prices')
    const balance = items.find((item) => item.getAttribute('data-widget-id') === 'balance')

    if (!prices || !balance) throw new Error('Dashboard widgets did not render')
    fireEvent.dragStart(prices)
    fireEvent.dragOver(balance)
    fireEvent.drop(balance)

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith({
        dashboard_layout: ['prices', 'balance', 'usage', 'usage_leaderboard'],
      })
    })
  })
})
