import { fireEvent, render, screen, waitFor } from '../../test-utils'
import { SettingsDialog } from '@/components/settings/SettingsDialog'
import { useResetSettings, useSettings, useUpdateSettings } from '@/lib/hooks'

jest.mock('@/lib/hooks')

const mockUseSettings = useSettings as jest.MockedFunction<typeof useSettings>
const mockUseUpdateSettings = useUpdateSettings as jest.MockedFunction<typeof useUpdateSettings>
const mockUseResetSettings = useResetSettings as jest.MockedFunction<typeof useResetSettings>

const settings = {
  coingecko_holding_amount: 2750,
  diem_holding_amount: 0,
  vvv_holding_source: 'manual',
  vvv_wallet_address: '',
  benchmark_max_cost_usd: 5,
  benchmark_enable_billing_reconciliation: false,
  benchmark_judge_model: 'zai-org-glm-5-2',
  refresh_interval_seconds: 60,
  in_app_notifications_enabled: true,
  display_currency: 'USD',
  timezone: 'local',
  dashboard_layout: ['balance', 'usage', 'prices', 'usage_leaderboard'],
}

describe('SettingsDialog preferences', () => {
  const mutate = jest.fn()
  const reset = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    mockUseSettings.mockReturnValue({ data: settings, isLoading: false } as any)
    mockUseUpdateSettings.mockReturnValue({ mutate, isPending: false } as any)
    mockUseResetSettings.mockReturnValue({ mutate: reset, isPending: false } as any)
  })

  it('saves refresh, notification, currency, and timezone preferences', async () => {
    render(<SettingsDialog />)
    fireEvent.click(screen.getByRole('button', { name: 'Open settings' }))

    fireEvent.change(screen.getByLabelText(/Data refresh interval/i), {
      target: { value: '300' },
    })
    fireEvent.change(screen.getByLabelText('Display currency'), {
      target: { value: 'AUD' },
    })
    fireEvent.change(screen.getByLabelText(/Timezone/), {
      target: { value: 'Australia/Sydney' },
    })
    fireEvent.click(screen.getByLabelText('Show in-app notifications for new alerts'))
    fireEvent.click(screen.getByRole('button', { name: 'Save settings' }))

    await waitFor(() => {
      expect(mutate).toHaveBeenCalledWith(expect.objectContaining({
        refresh_interval_seconds: 300,
        in_app_notifications_enabled: false,
        display_currency: 'AUD',
        timezone: 'Australia/Sydney',
      }))
    })
  })

  it('rejects invalid refresh intervals before saving', () => {
    render(<SettingsDialog />)
    fireEvent.click(screen.getByRole('button', { name: 'Open settings' }))

    fireEvent.change(screen.getByLabelText(/Data refresh interval/i), {
      target: { value: '14' },
    })
    fireEvent.submit(document.querySelector('form') as HTMLFormElement)

    expect(mutate).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent(/between 15 and 900/i)
  })

  it('rejects non-step refresh intervals before saving', () => {
    render(<SettingsDialog />)
    fireEvent.click(screen.getByRole('button', { name: 'Open settings' }))

    fireEvent.change(screen.getByLabelText(/Data refresh interval/i), {
      target: { value: '100' },
    })
    fireEvent.submit(document.querySelector('form') as HTMLFormElement)

    expect(mutate).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('resets settings to environment defaults', () => {
    render(<SettingsDialog />)
    fireEvent.click(screen.getByRole('button', { name: 'Open settings' }))
    fireEvent.click(screen.getByRole('button', { name: 'Reset defaults' }))

    expect(reset).toHaveBeenCalledTimes(1)
  })
})
