import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { toast } from 'sonner'
import { NewsView } from '@/components/news/NewsView'
import { useAskNews, useNews, useNewsArticle, useNewsSearch } from '@/lib/hooks'

jest.mock('@/lib/hooks', () => ({
  useNews: jest.fn(),
  useNewsArticle: jest.fn(),
  useNewsSearch: jest.fn(),
  useAskNews: jest.fn(),
}))
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }))

const mockUseNews = useNews as jest.MockedFunction<typeof useNews>
const mockUseNewsArticle = useNewsArticle as jest.MockedFunction<typeof useNewsArticle>
const mockUseNewsSearch = useNewsSearch as jest.MockedFunction<typeof useNewsSearch>
const mockUseAskNews = useAskNews as jest.MockedFunction<typeof useAskNews>

beforeEach(() => {
  jest.clearAllMocks()
  mockUseNewsArticle.mockReturnValue(
    { data: undefined, isLoading: false } as unknown as ReturnType<typeof useNewsArticle>,
  )
  mockUseNewsSearch.mockReturnValue(
    { mutate: jest.fn(), isPending: false, data: undefined } as unknown as ReturnType<typeof useNewsSearch>,
  )
  mockUseAskNews.mockReturnValue(
    { mutate: jest.fn(), isPending: false, data: undefined } as unknown as ReturnType<typeof useAskNews>,
  )
})

describe('NewsView refresh notifications', () => {
  it('notifies when a manual refresh succeeds', async () => {
    mockUseNews.mockReturnValue({
      data: { articles: [] },
      isLoading: false,
      isError: false,
      isFetching: false,
      refetch: jest.fn().mockResolvedValue({ isError: false }),
    } as unknown as ReturnType<typeof useNews>)

    render(<NewsView />)
    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }))

    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('News refreshed'))
  })

  it('notifies when a manual refresh fails', async () => {
    mockUseNews.mockReturnValue({
      data: { articles: [] },
      isLoading: false,
      isError: false,
      isFetching: false,
      refetch: jest.fn().mockResolvedValue({ isError: true, error: new Error('Search timed out') }),
    } as unknown as ReturnType<typeof useNews>)

    render(<NewsView />)
    fireEvent.click(screen.getByRole('button', { name: 'Refresh' }))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Search timed out'))
  })
})