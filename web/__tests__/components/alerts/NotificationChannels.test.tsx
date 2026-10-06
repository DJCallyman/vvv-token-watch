import { fireEvent, render, screen } from '../../test-utils'
import { NotificationChannels } from '@/components/alerts/NotificationChannels'
import {
  useCreateNotificationChannel,
  useDeleteNotificationChannel,
  useNotificationChannels,
  useNotificationDeliveries,
  useNotificationProviders,
  useRetryNotificationDelivery,
  useTestNotificationChannel,
  useVapidPublicKey,
} from '@/lib/hooks'

jest.mock('@/lib/hooks')

const mockUseChannels = useNotificationChannels as jest.MockedFunction<typeof useNotificationChannels>
const mockUseDeliveries = useNotificationDeliveries as jest.MockedFunction<typeof useNotificationDeliveries>
const mockUseCreate = useCreateNotificationChannel as jest.MockedFunction<typeof useCreateNotificationChannel>
const mockUseDelete = useDeleteNotificationChannel as jest.MockedFunction<typeof useDeleteNotificationChannel>
const mockUseTest = useTestNotificationChannel as jest.MockedFunction<typeof useTestNotificationChannel>
const mockUseRetry = useRetryNotificationDelivery as jest.MockedFunction<typeof useRetryNotificationDelivery>
const mockUseProviders = useNotificationProviders as jest.MockedFunction<typeof useNotificationProviders>
const mockUseVapid = useVapidPublicKey as jest.MockedFunction<typeof useVapidPublicKey>

const create = { mutate: jest.fn(), isPending: false }
const remove = { mutate: jest.fn(), isPending: false }
const test = { mutate: jest.fn(), isPending: false }
const retry = { mutate: jest.fn(), isPending: false }

beforeEach(() => {
  jest.clearAllMocks()
  mockUseChannels.mockReturnValue({
    data: {
      channels: [
        {
          id: 1,
          kind: 'discord',
          name: 'ops',
          enabled: true,
          destination: 'https://discord.com/…/42/****',
          webhook_url_masked: 'https://discord.com/…/42/****',
          created_at: null,
          updated_at: null,
        },
      ],
      count: 1,
    },
    isLoading: false,
    isError: false,
  } as any)
  mockUseDeliveries.mockReturnValue({
    data: {
      deliveries: [
        {
          id: 5,
          alert_event_id: 9,
          channel_id: 1,
          channel_name: 'ops',
          channel_kind: 'discord',
          status: 'failed',
          attempts: 3,
          last_error: 'Discord returned HTTP 500',
          next_attempt_at: null,
          created_at: null,
          updated_at: null,
        },
      ],
      count: 1,
    },
  } as any)
  mockUseProviders.mockReturnValue({
    data: {
      providers: [
        { kind: 'discord', available: true },
        { kind: 'slack', available: true },
        { kind: 'telegram', available: true },
        { kind: 'webhook', available: true },
        { kind: 'email', available: false },
        { kind: 'browser_push', available: false },
      ],
    },
  } as any)
  mockUseVapid.mockReturnValue({ data: { status: 'unavailable', reason: 'vapid_keys_not_configured' } } as any)
  mockUseCreate.mockReturnValue(create as any)
  mockUseDelete.mockReturnValue(remove as any)
  mockUseTest.mockReturnValue(test as any)
  mockUseRetry.mockReturnValue(retry as any)
})

describe('NotificationChannels', () => {
  it('never renders the raw webhook URL', () => {
    render(<NotificationChannels />)
    expect(screen.getByText('https://discord.com/…/42/****')).toBeInTheDocument()
    expect(document.body.innerHTML).not.toContain('topsecret')
  })

  it('rejects a non-https webhook before calling the API', () => {
    render(<NotificationChannels />)
    fireEvent.change(screen.getByLabelText('Channel name'), { target: { value: 'ops' } })
    fireEvent.change(screen.getByLabelText('Discord webhook URL'), {
      target: { value: 'http://discord.com/api/webhooks/1/x' },
    })
    fireEvent.click(screen.getByRole('button', { name: /add channel/i }))

    expect(create.mutate).not.toHaveBeenCalled()
    expect(screen.getAllByRole('alert').map((el) => el.textContent).join(' ')).toMatch(/https/i)
  })

  it('submits a valid Discord webhook', () => {
    render(<NotificationChannels />)
    fireEvent.change(screen.getByLabelText('Channel name'), { target: { value: 'ops' } })
    fireEvent.change(screen.getByLabelText('Discord webhook URL'), {
      target: { value: 'https://discord.com/api/webhooks/1/token' },
    })
    fireEvent.click(screen.getByRole('button', { name: /add channel/i }))

    expect(create.mutate).toHaveBeenCalledWith(
      { name: 'ops', kind: 'discord', webhook_url: 'https://discord.com/api/webhooks/1/token' },
      expect.any(Object),
    )
  })

  it('switches provider-specific fields and requires telegram credentials', () => {
    render(<NotificationChannels />)
    fireEvent.change(screen.getByLabelText('Provider'), { target: { value: 'telegram' } })
    fireEvent.change(screen.getByLabelText('Channel name'), { target: { value: 'tg' } })
    fireEvent.click(screen.getByRole('button', { name: /add channel/i }))

    expect(create.mutate).not.toHaveBeenCalled()
    expect(screen.getAllByRole('alert').map((el) => el.textContent).join(' ')).toMatch(/bot token/i)
  })

  it('marks unconfigured providers unavailable', () => {
    render(<NotificationChannels />)
    expect(screen.getByRole('option', { name: /email.*not configured/i })).toBeDisabled()
    expect(screen.getByRole('option', { name: /browser push.*not configured/i })).toBeDisabled()
  })

  it('shows failed deliveries with a retry action', () => {
    render(<NotificationChannels />)
    expect(screen.getByText(/1 delivery failure/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(retry.mutate).toHaveBeenCalledWith(5)
  })

  it('sends a test message for a configured channel', () => {
    render(<NotificationChannels />)
    fireEvent.click(screen.getByRole('button', { name: 'Send test' }))
    expect(test.mutate).toHaveBeenCalledWith(1)
  })
})

