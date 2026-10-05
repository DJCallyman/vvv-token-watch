import type React from 'react'
import { act, fireEvent, render, screen, waitFor } from '../../test-utils'
import { toast } from 'sonner'
import { CommandPalette } from '@/components/layout/CommandPalette'
import { useTheme } from '@/components/ThemeProvider'

const mockPush = jest.fn()
let mockPathname = '/'
const mockToggleTheme = jest.fn()

jest.mock('next/navigation', () => ({
  usePathname: () => mockPathname,
  useRouter: () => ({ push: mockPush }),
}))
jest.mock('@/components/ThemeProvider', () => ({
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
  useTheme: jest.fn(),
}))
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }))

const mockUseTheme = useTheme as jest.MockedFunction<typeof useTheme>

beforeEach(() => {
  jest.clearAllMocks()
  mockPathname = '/'
  mockUseTheme.mockReturnValue({ theme: 'dark', setTheme: jest.fn(), toggleTheme: mockToggleTheme })
})

function openPalette() {
  fireEvent.keyDown(window, { key: 'k', ctrlKey: true })
}

describe('CommandPalette', () => {
  it('opens with Ctrl+K and navigates to a filtered route on Enter', () => {
    render(<CommandPalette />)
    openPalette()

    const search = screen.getByRole('textbox', { name: 'Search pages and actions' })
    fireEvent.change(search, { target: { value: 'page' } })
    fireEvent.keyDown(search, { key: 'ArrowDown' })
    fireEvent.keyDown(search, { key: 'Enter' })

    expect(mockPush).toHaveBeenCalledWith('/models')
  })

  it('opens from the shared header trigger event', () => {
    render(<CommandPalette />)
    act(() => window.dispatchEvent(new Event('vvv:open-command-palette')))

    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('runs the refresh action and confirms completion', async () => {
    render(<CommandPalette />)
    openPalette()

    const search = screen.getByRole('textbox', { name: 'Search pages and actions' })
    fireEvent.change(search, { target: { value: 'refresh data' } })
    fireEvent.keyDown(search, { key: 'Enter' })

    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Data refreshed'))
  })

  it('does not expose app commands on the login page', () => {
    mockPathname = '/login'
    render(<CommandPalette />)
    openPalette()

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})