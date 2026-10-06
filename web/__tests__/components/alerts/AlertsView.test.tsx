import { fireEvent, screen, waitFor } from '@testing-library/react'
import { render } from '../../test-utils'
import { AlertsView } from '@/components/alerts/AlertsView'
import { api } from '@/lib/api'
import { useAlerts, useAlertEvents } from '@/lib/hooks'
import { toast } from 'sonner'

jest.mock('@/lib/hooks', () => ({
  useAlerts: jest.fn(),
  useAlertEvents: jest.fn(),
}))
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }))

beforeEach(() => {
  jest.clearAllMocks()
  jest.mocked(useAlerts).mockReturnValue({ data: { alerts: [], count: 0 }, isLoading: false, isError: false } as never)
  jest.mocked(useAlertEvents).mockReturnValue({ data: { events: [] }, isLoading: false } as never)
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

  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Daily spend' } })
  fireEvent.click(screen.getByRole('button', { name: /create alert/i }))

  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Alert service unavailable'))
  expect(screen.getByRole('alert')).toHaveTextContent('Alert service unavailable')
})