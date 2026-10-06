import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { InfographicPanel } from '@/components/benchmark/InfographicPanel'
import { api } from '@/lib/api'
import { toast } from 'sonner'

jest.mock('@/lib/api', () => ({ api: { generateInfographic: jest.fn() } }))
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }))
jest.mock('next/image', () => ({
  __esModule: true,
  default: (props: React.ImgHTMLAttributes<HTMLImageElement>) => <img {...props} />,
}))

beforeEach(() => jest.clearAllMocks())

it('notifies when an infographic is generated', async () => {
  jest.mocked(api.generateInfographic).mockResolvedValue({ image_b64: 'aGVsbG8=' } as never)
  render(<InfographicPanel runId="run-1" />)

  fireEvent.click(screen.getByRole('button', { name: 'Generate Infographic' }))

  await waitFor(() => expect(toast.success).toHaveBeenCalledWith('Infographic generated'))
  expect(screen.getByRole('img', { name: 'Benchmark infographic' })).toBeInTheDocument()
})

it('notifies when infographic generation fails', async () => {
  jest.mocked(api.generateInfographic).mockRejectedValue(new Error('Image service unavailable'))
  render(<InfographicPanel runId="run-1" />)

  fireEvent.click(screen.getByRole('button', { name: 'Generate Infographic' }))

  await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Image service unavailable'))
  expect(screen.getByText('Image service unavailable')).toBeInTheDocument()
})