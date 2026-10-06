import { fireEvent, screen, waitFor } from '@testing-library/react'
import { render } from '../../test-utils'
import { AlertsView } from '@/components/alerts/AlertsView'
import { api } from '@/lib/api'
import {
  useAlertEvents,
  useAlerts,
  useAlertVoice,
  useCreateNotificationChannel,
  useDeleteNotificationChannel,
  useNotificationChannels,
  useNotificationDeliveries,
  useNotificationProviders,
  useRetryNotificationDelivery,
  useTestNotificationChannel,
  useVapidPublicKey,
} from '@/lib/hooks'
import { toast } from 'sonner'

jest.mock('@/lib/hooks', () => ({
  useAlerts: jest.fn(),
  useAlertEvents: jest.fn(),
  useAlertVoice: jest.fn(),
  useNotificationChannels: jest.fn(),
  useCreateNotificationChannel: jest.fn(),
  useDeleteNotificationChannel: jest.fn(),
  useTestNotificationChannel: jest.fn(),
  useNotificationDeliveries: jest.fn(),
  useRetryNotificationDelivery: jest.fn(),
  useNotificationProviders: jest.fn(),
  useVapidPublicKey: jest.fn(),
}))
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }))

beforeEach(() => {
  jest.clearAllMocks()
  jest.mocked(useAlerts).mockReturnValue({ data: { alerts: [], count: 0 }, isLoading: false, isError: false } as never)
  jest.mocked(useAlertEvents).mockReturnValue({ data: { events: [] }, isLoading: false } as never)
  jest.mocked(useAlertVoice).mockReturnValue({ mutate: jest.fn(), isPending: false } as never)
  jest.mocked(useNotificationChannels).mockReturnValue({ data: { channels: [], count: 0 }, isLoading: false, isError: false } as never)
  jest.mocked(useCreateNotificationChannel).mockReturnValue({ mutate: jest.fn(), isPending: false } as never)
  jest.mocked(useDeleteNotificationChannel).mockReturnValue({ mutate: jest.fn() } as never)
  jest.mocked(useTestNotificationChannel).mockReturnValue({ mutate: jest.fn(), isPending: false } as never)
  jest.mocked(useNotificationDeliveries).mockReturnValue({ data: { deliveries: [], count: 0 } } as never)
  jest.mocked(useRetryNotificationDelivery).mockReturnValue({ mutate: jest.fn(), isPending: false } as never)
  jest.mocked(useNotificationProviders).mockReturnValue({ data: { providers: [] } } as never)
  jest.mocked(useVapidPublicKey).mockReturnValue({ data: { status: 'unavailable' } } as never)
})

it('shows content-shaped loading states for alerts and recent events', () => {
  jest.mocked(useAlerts).mockReturnValue({ data: undefined, isLoading: true, isError: false } as never)
  jest.mocked(useAlertEvents).mockReturnValue({ data: undefined, isLoading: true } as never)
  render(<AlertsView />)

  expect(screen.getByRole('region', { name: 'Loading configured alerts' })).toHaveAttribute('aria-busy', 'true')
  expect(screen.getByRole('region', { name: 'Loading recent alert events' })).toHaveAttribute('aria-busy', 'true')
})

it('shows a toast when alert creation fails', async () => {
  jest.spyOn(api, 'createAlert').mockRejectedValue(new Error('Alert service unavailable'))
  render(<AlertsView />)

  fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Daily spend' } })
  fireEvent.click(screen.getByRole('button', { name: /create alert/i }))

  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Alert service unavailable'))
  expect(screen.getByRole('alert')).toHaveTextContent('Alert service unavailable')
})
