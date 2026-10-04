import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { BenchmarkView } from '@/components/benchmark/BenchmarkView'
import { api } from '@/lib/api'
import { toast } from 'sonner'

jest.mock('@/lib/hooks', () => ({
  useBenchmarkRuns: () => ({ data: { runs: [] }, isLoading: false, refetch: jest.fn().mockResolvedValue({ isError: false }) }),
  useBenchmarkRun: () => ({ data: undefined, isLoading: false }),
}))
jest.mock('@/lib/api', () => ({ api: { startBenchmark: jest.fn() } }))
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn(), info: jest.fn() } }))
jest.mock('@/components/benchmark/RunConfig', () => ({
  RunConfig: ({ onStart }: { onStart: (params: { models: string[] }) => void }) => (
    <button type="button" onClick={() => onStart({ models: ['model-a'] })}>Start test run</button>
  ),
}))
jest.mock('@/components/benchmark/BenchmarkProgress', () => ({
  BenchmarkProgress: ({
    onComplete,
    onError,
    onCancelled,
  }: {
    onComplete: (runId: string) => void
    onError: (message: string) => void
    onCancelled: () => void
  }) => (
    <div>
      <button type="button" onClick={() => onComplete('run-1')}>Complete test run</button>
      <button type="button" onClick={() => onError('Benchmark failed')}>Fail test run</button>
      <button type="button" onClick={onCancelled}>Cancel test run</button>
    </div>
  ),
}))

beforeEach(() => jest.clearAllMocks())

async function startRun() {
  jest.mocked(api.startBenchmark).mockResolvedValue({ job_id: 'job-1' } as never)
  render(<BenchmarkView />)
  fireEvent.click(screen.getAllByRole('button', { name: 'Run Benchmark' })[0])
  fireEvent.click(screen.getByRole('button', { name: 'Start test run' }))
  await screen.findByRole('button', { name: 'Complete test run' })
}

it('notifies when a benchmark starts', async () => {
  jest.mocked(api.startBenchmark).mockResolvedValue({ job_id: 'job-1' } as never)
  render(<BenchmarkView />)
  fireEvent.click(screen.getAllByRole('button', { name: 'Run Benchmark' })[0])
  fireEvent.click(screen.getByRole('button', { name: 'Start test run' }))

  await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Benchmark started'))
})

it('notifies on benchmark completion, failure, and cancellation', async () => {
  await startRun()
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: 'Complete test run' }))
    await Promise.resolve()
  })
  expect(toast.success).toHaveBeenCalledWith('Benchmark complete')
})

it('notifies when a benchmark fails', async () => {
  await startRun()
  await screen.findByRole('button', { name: 'Fail test run' })
  fireEvent.click(screen.getByRole('button', { name: 'Fail test run' }))
  expect(toast.error).toHaveBeenCalledWith('Benchmark failed')
})

it('notifies when a benchmark is cancelled', async () => {
  await startRun()
  await screen.findByRole('button', { name: 'Cancel test run' })
  fireEvent.click(screen.getByRole('button', { name: 'Cancel test run' }))
  expect(toast.info).toHaveBeenCalledWith('Benchmark cancelled')
})