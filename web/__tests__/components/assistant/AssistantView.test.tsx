import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { api } from '@/lib/api'
import { toast } from 'sonner'
import { AssistantView } from '@/components/assistant/AssistantView'

jest.mock('@/lib/api', () => ({ api: { queryAssistant: jest.fn() } }))
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }))

const mockQueryAssistant = api.queryAssistant as jest.MockedFunction<typeof api.queryAssistant>

beforeEach(() => jest.clearAllMocks())

describe('AssistantView notifications', () => {
  it('shows a response-shaped loading state while waiting', () => {
    mockQueryAssistant.mockReturnValue(new Promise(() => {}))

    render(<AssistantView />)
    fireEvent.change(screen.getByRole('textbox', { name: /assistant question/i }), {
      target: { value: 'Summarize my usage' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }))

    expect(screen.getByText('Generating assistant response')).toBeInTheDocument()
    expect(screen.getByText('Generating assistant response').parentElement).toHaveAttribute(
      'aria-busy',
      'true',
    )
  })

  it('notifies when an answer is ready', async () => {
    mockQueryAssistant.mockResolvedValue({ answer: 'Usage is steady.', tool_calls: [] })

    render(<AssistantView />)
    fireEvent.change(screen.getByRole('textbox', { name: /assistant question/i }), {
      target: { value: 'Summarize my usage' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }))

    await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Assistant response ready'))
    expect(screen.getByText('Usage is steady.')).toBeInTheDocument()
  })

  it('notifies when the assistant request fails', async () => {
    mockQueryAssistant.mockRejectedValue(new Error('Assistant unavailable'))

    render(<AssistantView />)
    fireEvent.change(screen.getByRole('textbox', { name: /assistant question/i }), {
      target: { value: 'Summarize my usage' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }))

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Assistant unavailable'))
  })
})