import { fireEvent, screen, waitFor } from '@testing-library/react'
import { render } from '../../test-utils'
import { AlertsView } from '@/components/alerts/AlertsView'
import { api } from '@/lib/api'
import { toast } from 'sonner'

jest.mock('@/lib/hooks', () => ({
  useAlerts: () => ({ data: { alerts: [], count: 0 }, isLoading: false, isError: false }),
  useAlertEvents: () => ({ data: { events: [] }, isLoading: false }),
}))
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }))

beforeEach(() => jest.clearAllMocks())

it('shows a toast when alert creation fails', async () => {
  jest.spyOn(api, 'createAlert').mockRejectedValue(new Error('Alert service unavailable'))
  render(<AlertsView />)

  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Daily spend' } })
  fireEvent.click(screen.getByRole('button', { name: /create alert/i }))

  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Alert service unavailable'))
  expect(screen.getByRole('alert')).toHaveTextContent('Alert service unavailable')
})