import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { BenchmarkProgress } from '@/components/benchmark/BenchmarkProgress'
import { api } from '@/lib/api'
import { toast } from 'sonner'

jest.mock('@/lib/api', () => ({ api: { cancelBenchmark: jest.fn() } }))
jest.mock('sonner', () => ({ toast: { error: jest.fn() } }))

beforeEach(() => {
  jest.clearAllMocks()
  Object.defineProperty(globalThis, 'EventSource', {
    configurable: true,
    value: jest.fn(() => ({ close: jest.fn(), onmessage: null, onerror: null })),
  })
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
    configurable: true,
    value: jest.fn(),
  })
})

it('notifies when cancelling a benchmark fails', async () => {
  jest.mocked(api.cancelBenchmark).mockRejectedValue(new Error('Cancellation request failed'))
  render(<BenchmarkProgress jobId="job-1" onComplete={jest.fn()} />)

  fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

  await waitFor(() => {
    expect(toast.error).toHaveBeenCalledWith('Cancellation request failed')
  })
  expect(screen.getByText('Cancellation request failed')).toBeInTheDocument()
})