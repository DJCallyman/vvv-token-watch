import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ApiKeyFormModal } from '@/components/apikeys/ApiKeyFormModal'
import type { APIKeyUsage } from '@/lib/api'

const BASE_KEY: APIKeyUsage = {
  id: 'k1',
  name: 'Existing Key',
  diem_usage: 1.5,
  usd_usage: 0.5,
  created_at: '2026-01-01T00:00:00Z',
  is_active: true,
  api_key_type: 'INFERENCE',
  consumption_limits_usd: 10,
  limit_period: 'MONTH',
}

describe('ApiKeyFormModal — create mode', () => {
  it('renders create heading', () => {
    render(<ApiKeyFormModal mode="create" onClose={() => {}} onSubmit={() => {}} />)
    expect(screen.getByRole('dialog', { name: /create api key/i })).toBeInTheDocument()
  })

  it('does not pre-fill description in create mode', () => {
    render(<ApiKeyFormModal mode="create" onClose={() => {}} onSubmit={() => {}} />)
    const input = screen.getByLabelText(/description/i) as HTMLInputElement
    expect(input.value).toBe('')
  })

  it('renders both key type radio options', () => {
    render(<ApiKeyFormModal mode="create" onClose={() => {}} onSubmit={() => {}} />)
    expect(screen.getByRole('radio', { name: /inference/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /admin/i })).toBeInTheDocument()
  })

  it('disables submit when description is empty', () => {
    render(<ApiKeyFormModal mode="create" onClose={() => {}} onSubmit={() => {}} />)
    const submit = screen.getByRole('button', { name: /create key/i }) as HTMLButtonElement
    expect(submit.disabled).toBe(true)
  })

  it('enables submit when description is non-empty', async () => {
    const user = userEvent.setup()
    render(<ApiKeyFormModal mode="create" onClose={() => {}} onSubmit={() => {}} />)
    await user.type(screen.getByLabelText(/description/i), 'Mobile app key')
    const submit = screen.getByRole('button', { name: /create key/i }) as HTMLButtonElement
    expect(submit.disabled).toBe(false)
  })

  it('shows character count', async () => {
    const user = userEvent.setup()
    render(<ApiKeyFormModal mode="create" onClose={() => {}} onSubmit={() => {}} />)
    await user.type(screen.getByLabelText(/description/i), 'Hi')
    expect(screen.getByText(/2\/64 characters/i)).toBeInTheDocument()
  })

  it('submits payload with description and defaults', async () => {
    const user = userEvent.setup()
    const onSubmit = jest.fn()
    render(<ApiKeyFormModal mode="create" onClose={() => {}} onSubmit={onSubmit} />)
    await user.type(screen.getByLabelText(/description/i), 'Mobile app key')
    await user.click(screen.getByRole('button', { name: /create key/i }))

    expect(onSubmit).toHaveBeenCalledWith({
      apiKeyType: 'INFERENCE',
      description: 'Mobile app key',
      consumptionLimit: null,
      limitPeriod: null,
      expiresAt: null,
    })
  })

  it('passes consumption limit + period when provided', async () => {
    const user = userEvent.setup()
    const onSubmit = jest.fn()
    render(<ApiKeyFormModal mode="create" onClose={() => {}} onSubmit={onSubmit} />)
    await user.type(screen.getByLabelText(/description/i), 'Limited key')
    await user.clear(screen.getByLabelText(/USD/i))
    await user.type(screen.getByLabelText(/USD/i), '25')
    await user.selectOptions(screen.getByLabelText(/reset period/i), 'MONTH')

    await user.click(screen.getByRole('button', { name: /create key/i }))

    expect(onSubmit).toHaveBeenCalledWith({
      apiKeyType: 'INFERENCE',
      description: 'Limited key',
      consumptionLimit: { usd: 25, diem: null },
      limitPeriod: 'MONTH',
      expiresAt: null,
    })
  })

  it('calls onClose when Cancel clicked', async () => {
    const user = userEvent.setup()
    const onClose = jest.fn()
    render(<ApiKeyFormModal mode="create" onClose={onClose} onSubmit={() => {}} />)
    await user.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('allows type selection in create mode', async () => {
    const user = userEvent.setup()
    const onSubmit = jest.fn()
    render(<ApiKeyFormModal mode="create" onClose={() => {}} onSubmit={onSubmit} />)
    await user.click(screen.getByRole('radio', { name: /admin/i }))
    await user.type(screen.getByLabelText(/description/i), 'Admin key')
    await user.click(screen.getByRole('button', { name: /create key/i }))

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ apiKeyType: 'ADMIN' }),
    )
  })
})

describe('ApiKeyFormModal — edit mode', () => {
  it('renders edit heading', () => {
    render(
      <ApiKeyFormModal
        mode="edit"
        existing={BASE_KEY}
        onClose={() => {}}
        onSubmit={() => {}}
      />,
    )
    expect(screen.getByRole('dialog', { name: /edit api key/i })).toBeInTheDocument()
  })

  it('pre-fills description from existing', () => {
    render(
      <ApiKeyFormModal
        mode="edit"
        existing={BASE_KEY}
        onClose={() => {}}
        onSubmit={() => {}}
      />,
    )
    const input = screen.getByLabelText(/description/i) as HTMLInputElement
    expect(input.value).toBe('Existing Key')
  })

  it('locks key type in edit mode', () => {
    render(
      <ApiKeyFormModal
        mode="edit"
        existing={BASE_KEY}
        onClose={() => {}}
        onSubmit={() => {}}
      />,
    )
    expect(
      (screen.getByRole('radio', { name: /inference/i }) as HTMLInputElement).disabled,
    ).toBe(true)
    expect(
      (screen.getByRole('radio', { name: /admin/i }) as HTMLInputElement).disabled,
    ).toBe(true)
  })

  it('pre-fills consumption limits from existing', () => {
    render(
      <ApiKeyFormModal
        mode="edit"
        existing={BASE_KEY}
        onClose={() => {}}
        onSubmit={() => {}}
      />,
    )
    expect((screen.getByLabelText(/USD/i) as HTMLInputElement).value).toBe('10')
    expect((screen.getByLabelText(/reset period/i) as HTMLSelectElement).value).toBe('MONTH')
  })

  it('submits update with id field', async () => {
    const user = userEvent.setup()
    const onSubmit = jest.fn()
    render(
      <ApiKeyFormModal
        mode="edit"
        existing={BASE_KEY}
        onClose={() => {}}
        onSubmit={onSubmit}
      />,
    )
    await user.click(screen.getByRole('button', { name: /save changes/i }))

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'k1',
        description: 'Existing Key',
        limitPeriod: 'MONTH',
      }),
    )
  })
})

describe('ApiKeyFormModal — accessibility', () => {
  it('closes on Escape key', async () => {
    const user = userEvent.setup()
    const onClose = jest.fn()
    render(<ApiKeyFormModal mode="create" onClose={onClose} onSubmit={() => {}} />)
    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalled()
  })

  it('does not close on Escape while submitting', async () => {
    const user = userEvent.setup()
    const onClose = jest.fn()
    render(
      <ApiKeyFormModal
        mode="create"
        onClose={onClose}
        onSubmit={() => {}}
        submitting
      />,
    )
    await user.keyboard('{Escape}')
    expect(onClose).not.toHaveBeenCalled()
  })
})
