import { render, screen } from '../../test-utils'
import { UsageView } from '@/components/usage/UsageView'
import { useAPIKeyAnalytics, useAPIKeysUsage, useEpochUsage, useUsageTrends } from '@/lib/hooks'

jest.mock('@/lib/hooks', () => ({
  useAPIKeyAnalytics: jest.fn(),
  useAPIKeysUsage: jest.fn(),
  useEpochUsage: jest.fn(),
  useUsageTrends: jest.fn(),
}))

beforeEach(() => {
  jest.clearAllMocks()
  jest.mocked(useAPIKeyAnalytics).mockReturnValue({ data: undefined, isLoading: false } as never)
  jest.mocked(useAPIKeysUsage).mockReturnValue({
    data: undefined,
    isLoading: true,
    isError: false,
    refetch: jest.fn(),
  } as never)
  jest.mocked(useEpochUsage).mockReturnValue({
    data: undefined,
    isLoading: true,
    isError: false,
    refetch: jest.fn(),
  } as never)
  jest.mocked(useUsageTrends).mockReturnValue({ data: undefined, isLoading: true } as never)
})

it('shows content-shaped loading states for usage summaries and trends', () => {
  render(<UsageView />)

  expect(screen.getByRole('region', { name: 'Loading usage summary' })).toHaveAttribute('aria-busy', 'true')
  expect(screen.getByRole('region', { name: 'Loading usage trends' })).toHaveAttribute('aria-busy', 'true')
  expect(screen.getByRole('region', { name: 'Loading 7-day usage summary' })).toHaveAttribute('aria-busy', 'true')
})