import { fireEvent, render, screen } from '../../test-utils'
import { WatchlistCard } from '@/components/onchain/WatchlistCard'
import {
  useCreateWatchlistItem,
  useDeleteWatchlistItem,
  useWatchlist,
} from '@/lib/hooks'

jest.mock('@/lib/hooks')

const mockUseWatchlist = useWatchlist as jest.MockedFunction<typeof useWatchlist>
const mockUseCreate = useCreateWatchlistItem as jest.MockedFunction<typeof useCreateWatchlistItem>
const mockUseDelete = useDeleteWatchlistItem as jest.MockedFunction<typeof useDeleteWatchlistItem>

const create = { mutate: jest.fn(), isPending: false }
const remove = { mutate: jest.fn(), isPending: false }

beforeEach(() => {
  jest.clearAllMocks()
  mockUseWatchlist.mockReturnValue({
    data: {
      items: [
        {
          id: 3,
          chain: 'base-mainnet',
          token: 'vvv',
          address: '0x' + 'ab'.repeat(20),
          label: 'treasury',
          created_at: null,
        },
      ],
      count: 1,
    },
    isLoading: false,
    isError: false,
  } as any)
  mockUseCreate.mockReturnValue(create as any)
  mockUseDelete.mockReturnValue(remove as any)
})

describe('WatchlistCard', () => {
  it('lists persisted items with chain and token', () => {
    render(<WatchlistCard />)
    expect(screen.getByText('treasury')).toBeInTheDocument()
    expect(screen.getByText(/base-mainnet · VVV/)).toBeInTheDocument()
  })

  it('adds an address with an optional label', () => {
    render(<WatchlistCard />)
    fireEvent.change(screen.getByLabelText('Watchlist wallet address'), {
      target: { value: '0x' + 'cd'.repeat(20) },
    })
    fireEvent.change(screen.getByLabelText('Watchlist label'), { target: { value: 'cold' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add' }))

    expect(create.mutate).toHaveBeenCalledWith(
      { address: '0x' + 'cd'.repeat(20), label: 'cold' },
      expect.any(Object),
    )
  })

  it('disables add until an address is entered', () => {
    render(<WatchlistCard />)
    expect(screen.getByRole('button', { name: 'Add' })).toBeDisabled()
  })

  it('removes an item', () => {
    render(<WatchlistCard />)
    fireEvent.click(screen.getByRole('button', { name: /remove .* from watchlist/i }))
    expect(remove.mutate).toHaveBeenCalledWith(3)
  })

  it('shows an empty state', () => {
    mockUseWatchlist.mockReturnValue({ data: { items: [], count: 0 }, isLoading: false, isError: false } as any)
    render(<WatchlistCard />)
    expect(screen.getByText(/no watched wallets/i)).toBeInTheDocument()
  })
})
