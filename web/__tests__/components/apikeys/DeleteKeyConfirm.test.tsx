import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DeleteKeyConfirm } from '@/components/apikeys/DeleteKeyConfirm'
import type { APIKeyUsage } from '@/lib/api'

const TARGET: APIKeyUsage = {
  id: 'k1',
  name: 'Backup admin key',
  diem_usage: 0,
  usd_usage: 0,
  created_at: '2026-01-01T00:00:00Z',
  is_active: true,
  api_key_type: 'ADMIN',
}

function inDialog() {
  return screen.getByRole('alertdialog')
}

describe('DeleteKeyConfirm', () => {
  it('renders confirmation dialog', () => {
    render(
      <DeleteKeyConfirm apiKey={TARGET} onCancel={() => {}} onConfirm={() => {}} />,
    )
    expect(
      screen.getByRole('alertdialog', { name: /delete api key/i }),
    ).toBeInTheDocument()
  })

  it('shows the key name in destructive copy', () => {
    render(
      <DeleteKeyConfirm apiKey={TARGET} onCancel={() => {}} onConfirm={() => {}} />,
    )
    expect(screen.getByText(/Backup admin key/)).toBeInTheDocument()
    expect(screen.getByText(/permanently revoke/i)).toBeInTheDocument()
    expect(screen.getByText(/cannot be undone/i)).toBeInTheDocument()
  })

  it('renders Cancel and Delete buttons', () => {
    render(
      <DeleteKeyConfirm apiKey={TARGET} onCancel={() => {}} onConfirm={() => {}} />,
    )
    expect(inDialog().querySelector('button[type="button"]:not([aria-label])')).toBeInTheDocument()
    const buttons = inDialog().querySelectorAll('button')
    const deleteBtn = Array.from(buttons).find((b) => /delete key/i.test(b.textContent ?? ''))
    const cancelBtn = Array.from(buttons).find(
      (b) => b.textContent?.trim() === 'Cancel',
    )
    expect(deleteBtn).toBeDefined()
    expect(cancelBtn).toBeDefined()
  })

  it('calls onConfirm when Delete clicked', async () => {
    const user = userEvent.setup()
    const onConfirm = jest.fn()
    render(
      <DeleteKeyConfirm
        apiKey={TARGET}
        onCancel={() => {}}
        onConfirm={onConfirm}
      />,
    )
    const buttons = inDialog().querySelectorAll('button')
    const deleteBtn = Array.from(buttons).find((b) => /delete key/i.test(b.textContent ?? '')) as HTMLElement
    await user.click(deleteBtn)
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('calls onCancel when Cancel clicked', async () => {
    const user = userEvent.setup()
    const onCancel = jest.fn()
    render(
      <DeleteKeyConfirm
        apiKey={TARGET}
        onCancel={onCancel}
        onConfirm={() => {}}
      />,
    )
    const buttons = inDialog().querySelectorAll('button')
    const cancelBtn = Array.from(buttons).find(
      (b) => b.textContent?.trim() === 'Cancel',
    ) as HTMLElement
    await user.click(cancelBtn)
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('disables both buttons while submitting', () => {
    render(
      <DeleteKeyConfirm
        apiKey={TARGET}
        onCancel={() => {}}
        onConfirm={() => {}}
        submitting
      />,
    )
    const buttons = inDialog().querySelectorAll('button')
    const deleteBtn = Array.from(buttons).find((b) => /deleting/i.test(b.textContent ?? ''))
    const cancelBtn = Array.from(buttons).find(
      (b) => b.textContent?.trim() === 'Cancel',
    )
    expect((deleteBtn as HTMLButtonElement).disabled).toBe(true)
    expect((cancelBtn as HTMLButtonElement).disabled).toBe(true)
  })

  it('changes Delete button label when submitting', () => {
    render(
      <DeleteKeyConfirm
        apiKey={TARGET}
        onCancel={() => {}}
        onConfirm={() => {}}
        submitting
      />,
    )
    expect(inDialog().textContent).toMatch(/Deleting/)
  })

  it('closes on Escape key', async () => {
    const user = userEvent.setup()
    const onCancel = jest.fn()
    render(
      <DeleteKeyConfirm apiKey={TARGET} onCancel={onCancel} onConfirm={() => {}} />,
    )
    await user.keyboard('{Escape}')
    expect(onCancel).toHaveBeenCalled()
  })
})
