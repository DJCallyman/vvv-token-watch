import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { toast } from 'sonner'
import { NewsView } from '@/components/news/NewsView'
import { useNews, useNewsArticle } from '@/lib/hooks'

jest.mock('@/lib/hooks', () => ({
  useNews: jest.fn(),
  useNewsArticle: jest.fn(),
}))
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }))

const mockUseNews = useNews as jest.MockedFunction<typeof useNews>
const mockUseNewsArticle = useNewsArticle as jest.MockedFunction<typeof useNewsArticle>

beforeEach(() => {
  jest.clearAllMocks()
  mockUseNewsArticle.mockReturnValue(
    { data: undefined, isLoading: false } as unknown as ReturnType<typeof useNewsArticle>,
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
    fireEvent.click(screen.getByRole('button', { name: /refresh/i }))

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
    fireEvent.click(screen.getByRole('button', { name: /refresh/i }))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Search timed out'))
  })
})