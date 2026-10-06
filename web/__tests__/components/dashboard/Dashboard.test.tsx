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

// The dashboard also renders the onboarding checklist, which uses <li>
// elements; scope layout assertions to widgets that carry data-widget-id.
const widgetIds = () =>
  screen
    .getAllByRole('listitem')
    .map((item) => item.getAttribute('data-widget-id'))
    .filter((id): id is string => id !== null)

beforeEach(() => {
  window.localStorage.clear()
})

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

  it('applies the stored layout on mount', () => {
    mockUseSettings.mockReturnValue({
      data: { dashboard_layout: ['prices', 'balance', 'usage', 'usage_leaderboard'] },
      isLoading: false,
    } as any)

    render(<Dashboard />)

    expect(widgetIds()).toEqual(['prices', 'balance', 'usage', 'usage_leaderboard'])
  })

  it('rolls back the optimistic layout when saving fails', async () => {
    mutateAsync.mockRejectedValueOnce(new Error('save failed'))
    render(<Dashboard />)

    fireEvent.click(screen.getByRole('button', { name: 'Move Token prices up' }))

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalled()
    })
    await waitFor(() => {
      expect(widgetIds()).toEqual(['balance', 'usage', 'prices', 'usage_leaderboard'])
    })
  })

  it('disables move controls at list bounds', () => {
    render(<Dashboard />)

    expect(screen.getByRole('button', { name: 'Move Account balance up' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Move API key usage down' })).toBeDisabled()
  })

  it('keeps every widget reachable at mobile and desktop viewport sizes', () => {
    const { unmount } = render(<Dashboard />)
    const grid = screen.getByRole('list', { name: 'Dashboard widgets' })
    // Responsive single-column layout expands to a three-column grid on lg+.
    expect(grid.className).toContain('grid-cols-1')
    expect(grid.className).toContain('lg:grid-cols-3')
    expect(widgetIds()).toHaveLength(4)

    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 375 })
    window.dispatchEvent(new Event('resize'))
    expect(widgetIds()).toHaveLength(4)

    unmount()
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 1440 })
    render(<Dashboard />)
    expect(widgetIds()).toHaveLength(4)
  })
})
