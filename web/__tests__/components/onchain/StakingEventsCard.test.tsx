import { fireEvent, render, screen } from '../../test-utils'
import { StakingEventsCard } from '@/components/onchain/StakingEventsCard'
import { useStakingEvents } from '@/lib/hooks'

jest.mock('@/lib/hooks')

const mockUseStakingEvents = useStakingEvents as jest.MockedFunction<typeof useStakingEvents>

beforeEach(() => {
  jest.clearAllMocks()
})

describe('StakingEventsCard', () => {
  it('renders stake and unstake directions with source attribution', () => {
    mockUseStakingEvents.mockReturnValue({
      data: {
        chain: 'base-mainnet',
        network: 'base-mainnet',
        token_symbol: 'VVV',
        staking_contract: '0x321b',
        address: null,
        events: [
          { direction: 'stake', counterparty: '0x' + 'ab'.repeat(20), value: '1', value_human: 1, tx_hash: '0x' + 'cd'.repeat(32), block_number: '0x1', log_index: '0x0' },
          { direction: 'unstake', counterparty: '0x' + 'ef'.repeat(20), value: '2', value_human: 2, tx_hash: '0x' + '11'.repeat(32), block_number: '0x2', log_index: '0x1' },
        ],
        count: 2,
        truncated: false,
        from_block: '0x1',
        to_block: '0x64',
        source: 'venice-rpc eth_getLogs',
        note: 'Only the reported block range is queried.',
      },
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    } as any)

    render(<StakingEventsCard />)
    expect(screen.getByText('Stake')).toBeInTheDocument()
    expect(screen.getByText('Unstake')).toBeInTheDocument()
    expect(screen.getByText(/Only the reported block range is queried/)).toBeInTheDocument()
  })

  it('shows an empty state for a range with no events', () => {
    mockUseStakingEvents.mockReturnValue({
      data: { events: [], count: 0, truncated: false, from_block: '0x1', to_block: '0x2', source: 'rpc', note: '' },
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    } as any)

    render(<StakingEventsCard />)
    expect(screen.getByText(/no staking events/i)).toBeInTheDocument()
  })

  it('shows a retryable error state when upstream fails', () => {
    const refetch = jest.fn()
    mockUseStakingEvents.mockReturnValue({ data: undefined, isLoading: false, isError: true, refetch } as any)

    render(<StakingEventsCard />)
    expect(screen.getByText(/could not load staking events/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(refetch).toHaveBeenCalled()
  })

  it('re-queries when the block range changes', () => {
    mockUseStakingEvents.mockReturnValue({
      data: { events: [], count: 0, truncated: false, from_block: '0x1', to_block: '0x2', source: 'rpc', note: '' },
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    } as any)

    render(<StakingEventsCard address={'0x' + 'ab'.repeat(20)} />)
    fireEvent.change(screen.getByLabelText('Staking event block range'), { target: { value: '50000' } })
    expect(mockUseStakingEvents).toHaveBeenLastCalledWith(50000, '0x' + 'ab'.repeat(20))
  })
})
