import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { RunConfig } from '@/components/benchmark/RunConfig'
import { api } from '@/lib/api'
import { toast } from 'sonner'

jest.mock('@/lib/api', () => ({ api: { estimateBenchmark: jest.fn() } }))
jest.mock('@/lib/hooks', () => ({ useBenchmarkModels: () => ({ data: { models: [] } }) }))
jest.mock('@/components/benchmark/ModelSelector', () => ({ ModelSelector: () => null }))
jest.mock('@/components/benchmark/TestSelector', () => ({ TestSelector: () => null }))
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }))

beforeEach(() => jest.clearAllMocks())

it('notifies when a benchmark cost estimate is ready', async () => {
  jest.mocked(api.estimateBenchmark).mockResolvedValue({
    model_count: 1,
    tests: ['text'],
    iterations: 10,
    estimated_calls: 10,
    estimated_usd: 0.25,
    judge_cost_usd: 0,
    workers: 4,
    skipped_tests_note: null,
    note: 'Estimate',
    model_ids: ['model-a'],
  } as never)
  render(<RunConfig onStart={jest.fn()} isRunning={false} />)

  fireEvent.click(screen.getByRole('button', { name: 'Estimate Cost' }))

  await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Benchmark cost estimate ready'))
})

it('notifies when benchmark cost estimation fails', async () => {
  jest.mocked(api.estimateBenchmark).mockRejectedValue(new Error('Pricing unavailable'))
  render(<RunConfig onStart={jest.fn()} isRunning={false} />)

  fireEvent.click(screen.getByRole('button', { name: 'Estimate Cost' }))

  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Pricing unavailable'))
  expect(screen.getByText('Pricing unavailable')).toBeInTheDocument()
})