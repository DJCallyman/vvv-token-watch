import React from 'react'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ApiKeysView } from '@/components/apikeys/ApiKeysView'
import {
  useAPIKeysUsage,
  useCreateAPIKey,
  useUpdateAPIKey,
  useDeleteAPIKey,
} from '@/lib/hooks'
import type { APIKeyUsage } from '@/lib/api'

jest.mock('@/lib/hooks')

const mockUseAPIKeysUsage = useAPIKeysUsage as jest.MockedFunction<typeof useAPIKeysUsage>
const mockUseCreateAPIKey = useCreateAPIKey as jest.MockedFunction<typeof useCreateAPIKey>
const mockUseUpdateAPIKey = useUpdateAPIKey as jest.MockedFunction<typeof useUpdateAPIKey>
const mockUseDeleteAPIKey = useDeleteAPIKey as jest.MockedFunction<typeof useDeleteAPIKey>

const SAMPLE_KEYS: APIKeyUsage[] = [
  {
    id: 'k-inference',
    name: 'CI runner',
    diem_usage: 5.25,
    usd_usage: 1.05,
    created_at: '2026-01-15T00:00:00Z',
    is_active: true,
    api_key_type: 'INFERENCE',
    last6_chars: 'ci1234',
    consumption_limits_usd: 10,
    limit_period: 'MONTH',
  },
  {
    id: 'k-admin',
    name: 'Backup admin',
    diem_usage: 0,
    usd_usage: 0,
    created_at: '2026-02-01T00:00:00Z',
    is_active: false,
    api_key_type: 'ADMIN',
    last6_chars: 'ad5678',
  },
]

function setupMutations() {
  mockUseCreateAPIKey.mockReturnValue({
    mutateAsync: jest.fn(),
    isPending: false,
  } as any)
  mockUseUpdateAPIKey.mockReturnValue({
    mutateAsync: jest.fn(),
    isPending: false,
  } as any)
  mockUseDeleteAPIKey.mockReturnValue({
    mutateAsync: jest.fn(),
    isPending: false,
  } as any)
}

describe('ApiKeysView — loading', () => {
  beforeEach(() => {
    setupMutations()
    mockUseAPIKeysUsage.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as any)
  })

  it('shows loading placeholder', () => {
    render(<ApiKeysView />)
    expect(screen.getByText(/loading api keys/i)).toBeInTheDocument()
  })
})

describe('ApiKeysView — error', () => {
  beforeEach(() => {
    setupMutations()
    mockUseAPIKeysUsage.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as any)
  })

  it('shows error message', () => {
    render(<ApiKeysView />)
    expect(screen.getByText(/failed to load api keys/i)).toBeInTheDocument()
  })
})

describe('ApiKeysView — populated', () => {
  beforeEach(() => {
    setupMutations()
    mockUseAPIKeysUsage.mockReturnValue({
      data: { keys: SAMPLE_KEYS },
      isLoading: false,
      isError: false,
    } as any)
  })

  it('renders header', () => {
    render(<ApiKeysView />)
    expect(screen.getByRole('heading', { name: /api keys/i })).toBeInTheDocument()
  })

  it('renders Create Key button', () => {
    render(<ApiKeysView />)
    expect(screen.getByRole('button', { name: /create key/i })).toBeInTheDocument()
  })

  it('renders both keys', () => {
    render(<ApiKeysView />)
    expect(screen.getByText('CI runner')).toBeInTheDocument()
    expect(screen.getByText('Backup admin')).toBeInTheDocument()
  })

  it('renders type badge INFERENCE for inference key', () => {
    render(<ApiKeysView />)
    expect(screen.getAllByText('INFERENCE').length).toBeGreaterThan(0)
  })

  it('renders type badge ADMIN for admin key', () => {
    render(<ApiKeysView />)
    expect(screen.getByText('ADMIN')).toBeInTheDocument()
  })

  it('renders Active badge for active key', () => {
    render(<ApiKeysView />)
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('renders Inactive badge for inactive key', () => {
    render(<ApiKeysView />)
    expect(screen.getByText('Inactive')).toBeInTheDocument()
  })

  it('shows consumption limit info when set', () => {
    render(<ApiKeysView />)
    expect(screen.getByText(/10 USD/i)).toBeInTheDocument()
    expect(screen.getAllByText(/month/i).length).toBeGreaterThan(0)
  })

  it('shows Unlimited label for key without limits', () => {
    render(<ApiKeysView />)
    expect(screen.getByText(/unlimited/i)).toBeInTheDocument()
  })

  it('renders edit and delete buttons for each key', () => {
    render(<ApiKeysView />)
    expect(screen.getByRole('button', { name: /edit ci runner/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /edit backup admin/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /delete ci runner/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /delete backup admin/i })).toBeInTheDocument()
  })

  it('renders last 6 chars snippet', () => {
    render(<ApiKeysView />)
    expect(screen.getByText('…ci1234')).toBeInTheDocument()
  })
})

describe('ApiKeysView — empty state', () => {
  beforeEach(() => {
    setupMutations()
    mockUseAPIKeysUsage.mockReturnValue({
      data: { keys: [] },
      isLoading: false,
      isError: false,
    } as any)
  })

  it('shows empty state guidance', () => {
    render(<ApiKeysView />)
    expect(screen.getByText(/no api keys yet/i)).toBeInTheDocument()
  })
})

describe('ApiKeysView — create flow', () => {
  beforeEach(() => {
    setupMutations()
    mockUseAPIKeysUsage.mockReturnValue({
      data: { keys: SAMPLE_KEYS },
      isLoading: false,
      isError: false,
    } as any)
  })

  it('opens create modal when Create Key clicked', async () => {
    const user = userEvent.setup()
    render(<ApiKeysView />)
    // Page-level button has the icon "create Key" (capital K).
    const pageButton = screen.getByRole('button', { name: /^create Key$/i })
    await user.click(pageButton)
    expect(screen.getByRole('dialog', { name: /create api key/i })).toBeInTheDocument()
  })

  it('shows one-time secret after successful create', async () => {
    const user = userEvent.setup()
    const mutateAsync = jest.fn().mockResolvedValue({
      data: {
        apiKey: 'venice_sk_live_super_secret_DO_NOT_LOOSE',
        id: 'new-key-id',
        apiKeyType: 'INFERENCE',
        description: 'My new key',
      },
      success: true,
    })
    mockUseCreateAPIKey.mockReturnValue({ mutateAsync, isPending: false } as any)

    render(<ApiKeysView />)
    await user.click(screen.getByRole('button', { name: /^create Key$/i }))

    const dialog = screen.getByRole('dialog', { name: /create api key/i })
    await user.type(within(dialog).getByLabelText(/description/i), 'My new key')

    // The submit button in the modal reads "Create key" (capital C, lowercase k).
    const submit = within(dialog).getByRole('button', { name: /^create key$/i })
    await user.click(submit)

    await waitFor(() => {
      expect(
        screen.getByDisplayValue('venice_sk_live_super_secret_DO_NOT_LOOSE'),
      ).toBeInTheDocument()
    })
    expect(
      screen.getByRole('dialog', { name: /save this api key now/i }),
    ).toBeInTheDocument()
  })

  it('shows error when create fails', async () => {
    const user = userEvent.setup()
    const mutateAsync = jest.fn().mockRejectedValue(new Error('You exceeded your limit'))
    mockUseCreateAPIKey.mockReturnValue({ mutateAsync, isPending: false } as any)

    render(<ApiKeysView />)
    await user.click(screen.getByRole('button', { name: /^create Key$/i }))
    const dialog = screen.getByRole('dialog', { name: /create api key/i })
    await user.type(within(dialog).getByLabelText(/description/i), 'Some key')
    await user.click(within(dialog).getByRole('button', { name: /^create key$/i }))

    await waitFor(() => {
      expect(screen.getByText(/exceeded your limit/i)).toBeInTheDocument()
    })
    // Modal should still be open so the user can fix and retry.
    expect(screen.getByRole('dialog', { name: /create api key/i })).toBeInTheDocument()
  })
})

describe('ApiKeysView — edit flow', () => {
  beforeEach(() => {
    setupMutations()
    mockUseAPIKeysUsage.mockReturnValue({
      data: { keys: SAMPLE_KEYS },
      isLoading: false,
      isError: false,
    } as any)
  })

  it('opens edit modal with pre-filled values', async () => {
    const user = userEvent.setup()
    render(<ApiKeysView />)
    await user.click(screen.getByRole('button', { name: /edit ci runner/i }))
    const dialog = screen.getByRole('dialog', { name: /edit api key/i })
    expect(dialog).toBeInTheDocument()
    expect(within(dialog).getByDisplayValue('CI runner')).toBeInTheDocument()
  })

  it('submits update on save', async () => {
    const user = userEvent.setup()
    const mutateAsync = jest.fn().mockResolvedValue({})
    mockUseUpdateAPIKey.mockReturnValue({ mutateAsync, isPending: false } as any)

    render(<ApiKeysView />)
    await user.click(screen.getByRole('button', { name: /edit ci runner/i }))
    const dialog = screen.getByRole('dialog', { name: /edit api key/i })
    const descriptionInput = within(dialog).getByDisplayValue('CI runner') as HTMLInputElement
    await user.clear(descriptionInput)
    await user.type(descriptionInput, 'CI runner (updated)')
    await user.click(within(dialog).getByRole('button', { name: /save changes/i }))

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          id: 'k-inference',
          description: 'CI runner (updated)',
        }),
      )
    })
  })
})

describe('ApiKeysView — delete flow', () => {
  beforeEach(() => {
    setupMutations()
    mockUseAPIKeysUsage.mockReturnValue({
      data: { keys: SAMPLE_KEYS },
      isLoading: false,
      isError: false,
    } as any)
  })

  it('opens delete confirmation when trash clicked', async () => {
    const user = userEvent.setup()
    render(<ApiKeysView />)
    await user.click(screen.getByRole('button', { name: /delete ci runner/i }))
    expect(
      screen.getByRole('alertdialog', { name: /delete api key/i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/this will permanently revoke/i)).toBeInTheDocument()
  })

  it('calls mutateAsync on confirm', async () => {
    const user = userEvent.setup()
    const mutateAsync = jest.fn().mockResolvedValue({ success: true, id: 'k-inference' })
    mockUseDeleteAPIKey.mockReturnValue({ mutateAsync, isPending: false } as any)

    render(<ApiKeysView />)
    await user.click(screen.getByRole('button', { name: /delete ci runner/i }))
    const dialog = screen.getByRole('alertdialog', { name: /delete api key/i })
    const deleteBtn = within(dialog).getByRole('button', { name: /^delete key$/i })
    await user.click(deleteBtn)

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith('k-inference')
    })
  })

  it('does not delete on cancel', async () => {
    const user = userEvent.setup()
    const mutateAsync = jest.fn()
    mockUseDeleteAPIKey.mockReturnValue({ mutateAsync, isPending: false } as any)

    render(<ApiKeysView />)
    await user.click(screen.getByRole('button', { name: /delete backup admin/i }))
    const dialog = screen.getByRole('alertdialog', { name: /delete api key/i })
    // The X close button has aria-label="Cancel"; the explicit Cancel button
    // has matching text — pick the one whose accessible name is just "Cancel".
    const buttons = within(dialog).getAllByRole('button')
    const cancelBtn = buttons.find((b) => b.textContent?.trim() === 'Cancel') as HTMLElement
    await user.click(cancelBtn)

    expect(mutateAsync).not.toHaveBeenCalled()
    expect(
      screen.queryByRole('alertdialog', { name: /delete api key/i }),
    ).not.toBeInTheDocument()
  })
})

describe('ApiKeysView — search and filter', () => {
  beforeEach(() => {
    setupMutations()
    mockUseAPIKeysUsage.mockReturnValue({
      data: { keys: SAMPLE_KEYS },
      isLoading: false,
      isError: false,
    } as any)
  })

  it('search filters by name', async () => {
    const user = userEvent.setup()
    render(<ApiKeysView />)
    await user.type(screen.getByPlaceholderText(/search by name/i), 'CI')
    await waitFor(() => {
      expect(screen.getByText('CI runner')).toBeInTheDocument()
      expect(screen.queryByText('Backup admin')).not.toBeInTheDocument()
    })
  })

  it('shows empty state when filter excludes all', async () => {
    const user = userEvent.setup()
    render(<ApiKeysView />)
    await user.type(screen.getByPlaceholderText(/search by name/i), 'nonexistent')
    await waitFor(() => {
      expect(screen.getByText(/no keys match your filters/i)).toBeInTheDocument()
    })
  })
})
