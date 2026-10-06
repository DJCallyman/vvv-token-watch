import { fireEvent, render, screen, waitFor } from '../../test-utils'
import { WalletSessionCard } from '@/components/onchain/WalletSessionCard'
import { api } from '@/lib/api'
import { useWalletBalance, useWalletTransactions } from '@/lib/hooks'

jest.mock('@/lib/hooks')

const mockUseWalletBalance = useWalletBalance as jest.MockedFunction<typeof useWalletBalance>
const mockUseWalletTransactions = useWalletTransactions as jest.MockedFunction<typeof useWalletTransactions>

const ADDRESS = '0x' + 'ab'.repeat(20)

function installProvider(personalSignResult: string | Error = '0xsigned') {
  const request = jest.fn(async ({ method }: { method: string }) => {
    if (method === 'eth_requestAccounts') return [ADDRESS]
    if (method === 'personal_sign') {
      if (personalSignResult instanceof Error) throw personalSignResult
      return personalSignResult
    }
    throw new Error(`unexpected method ${method}`)
  })
  ;(window as unknown as { ethereum?: { request: typeof request } }).ethereum = { request }
  return request
}

beforeEach(() => {
  jest.clearAllMocks()
  window.sessionStorage.clear()
  delete (window as unknown as { ethereum?: unknown }).ethereum
  mockUseWalletBalance.mockImplementation((token: string | null) =>
    (token
      ? {
          data: {
            address: ADDRESS,
            chain: 'base-mainnet',
            chain_id: 8453,
            holdings: {
              vvv_wallet: 10,
              svvv_total: 20,
              svvv_locked: 5,
              pending_rewards: 1,
              diem_wallet: 2,
              diem_staked: 3,
            },
            holdings_error: null,
            onchain: { vvv_balance: 10, chain: 'base-mainnet', token_symbol: 'VVV', network: 'base-mainnet', address: ADDRESS, token_address: '0x1', decimals: 18 },
            onchain_error: null,
            sources: ['venicestats'],
            read_only: true,
          },
          isLoading: false,
          isError: false,
          refetch: jest.fn(),
        }
      : { data: undefined, isLoading: false, isError: false, refetch: jest.fn() }) as never,
  )
  mockUseWalletTransactions.mockReturnValue({ data: undefined, isLoading: false, isError: false, refetch: jest.fn() } as never)
})

describe('WalletSessionCard', () => {
  it('completes the challenge/sign/verify flow and stores an opaque token', async () => {
    const request = installProvider('0xsigned')
    jest.spyOn(api, 'createWalletChallenge').mockResolvedValue({
      challenge_id: 1,
      address: ADDRESS,
      chain_id: 8453,
      message: 'sign me',
      expires_at: '2026-01-01T00:05:00Z',
    })
    jest.spyOn(api, 'verifyWalletChallenge').mockResolvedValue({
      token: 'opaque-token',
      address: ADDRESS,
      chain_id: 8453,
      expires_at: '2026-01-02T00:00:00Z',
    })

    render(<WalletSessionCard />)
    fireEvent.click(screen.getByRole('button', { name: /connect wallet/i }))

    await waitFor(() => expect(api.verifyWalletChallenge).toHaveBeenCalledWith(1, '0xsigned'))
    expect(window.sessionStorage.getItem('vvv:wallet-session-token')).toBe('opaque-token')
    expect(request).toHaveBeenCalledWith({ method: 'eth_requestAccounts' })
    await waitFor(() => expect(screen.getByText(/VVV on-chain balance/i)).toBeInTheDocument())
  })

  it('surfaces a missing wallet provider without calling the API', async () => {
    const createSpy = jest.spyOn(api, 'createWalletChallenge')
    render(<WalletSessionCard />)
    fireEvent.click(screen.getByRole('button', { name: /connect wallet/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/no browser wallet/i))
    expect(createSpy).not.toHaveBeenCalled()
  })

  it('restores a stored session token on mount', () => {
    window.sessionStorage.setItem('vvv:wallet-session-token', 'stored-token')
    render(<WalletSessionCard />)
    expect(screen.getByRole('button', { name: /disconnect/i })).toBeInTheDocument()
    expect(mockUseWalletBalance).toHaveBeenCalledWith('stored-token')
  })

  it('clears the session on disconnect', async () => {
    window.sessionStorage.setItem('vvv:wallet-session-token', 'stored-token')
    const logout = jest.spyOn(api, 'logoutWallet').mockResolvedValue({ logged_out: true })
    render(<WalletSessionCard />)
    fireEvent.click(screen.getByRole('button', { name: /disconnect/i }))

    await waitFor(() => expect(logout).toHaveBeenCalledWith('stored-token'))
    expect(window.sessionStorage.getItem('vvv:wallet-session-token')).toBeNull()
  })

  it('shows the error when signing fails', async () => {
    installProvider(new Error('user rejected'))
    jest.spyOn(api, 'createWalletChallenge').mockResolvedValue({
      challenge_id: 1,
      address: ADDRESS,
      chain_id: 8453,
      message: 'sign me',
      expires_at: '2026-01-01T00:05:00Z',
    })
    render(<WalletSessionCard />)
    fireEvent.click(screen.getByRole('button', { name: /connect wallet/i }))

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/user rejected/i))
  })
})
