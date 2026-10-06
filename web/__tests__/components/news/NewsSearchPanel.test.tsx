import { fireEvent, render, screen } from '../../test-utils'
import { NewsSearchPanel } from '@/components/news/NewsSearchPanel'
import { useAskNews, useNewsSearch } from '@/lib/hooks'

jest.mock('@/lib/hooks')

const mockUseSearch = useNewsSearch as jest.MockedFunction<typeof useNewsSearch>
const mockUseAsk = useAskNews as jest.MockedFunction<typeof useAskNews>

const search = { mutate: jest.fn(), isPending: false, data: undefined as unknown }
const ask = { mutate: jest.fn(), isPending: false, data: undefined as unknown }

beforeEach(() => {
  jest.clearAllMocks()
  search.data = undefined
  ask.data = undefined
  mockUseSearch.mockReturnValue(search as any)
  mockUseAsk.mockReturnValue(ask as any)
})

describe('NewsSearchPanel', () => {
  it('runs an embedding-ranked search and shows scores', () => {
    const view = render(<NewsSearchPanel />)
    fireEvent.change(screen.getByLabelText('Semantic news search query'), {
      target: { value: 'staking incentives' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))
    expect(search.mutate).toHaveBeenCalledWith({ query: 'staking incentives', topK: 5 })

    view.unmount()
    search.data = {
      results: [
        { title: 'Staking update', url: 'https://example.com/a', snippet: 's', score: 0.9123 },
      ],
    }
    render(<NewsSearchPanel />)
    expect(screen.getByText('Staking update')).toBeInTheDocument()
    expect(screen.getByText('score 0.912')).toBeInTheDocument()
  })

  it('asks a grounded question and cites sources', () => {
    ask.data = {
      answer: 'Staking pays DIEM.',
      sources: ['https://example.com/source'],
      retrieved: [],
    }
    render(<NewsSearchPanel />)
    expect(screen.getByText('Staking pays DIEM.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'https://example.com/source' })).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Ask a question about the news'), {
      target: { value: 'How does staking work?' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }))
    expect(ask.mutate).toHaveBeenCalledWith({ question: 'How does staking work?', topK: 5 })
  })

  it('disables submission for empty input', () => {
    render(<NewsSearchPanel />)
    expect(screen.getByRole('button', { name: 'Search' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Ask' })).toBeDisabled()
  })
})
