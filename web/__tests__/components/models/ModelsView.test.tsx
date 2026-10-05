import { fireEvent, render, screen } from '../../test-utils'
import { ModelsView } from '@/components/models/ModelsView'
import { useModelCompatibilityMapping, useModelTraits, useModels } from '@/lib/hooks'

jest.mock('@/lib/hooks')

const mockUseModels = useModels as jest.MockedFunction<typeof useModels>
const mockUseModelTraits = useModelTraits as jest.MockedFunction<typeof useModelTraits>
const mockUseModelCompatibility = useModelCompatibilityMapping as jest.MockedFunction<typeof useModelCompatibilityMapping>

beforeEach(() => {
  jest.clearAllMocks()
  mockUseModelTraits.mockReturnValue({ data: { data: {}, object: 'list', type: 'text' } } as ReturnType<typeof useModelTraits>)
  mockUseModelCompatibility.mockReturnValue({ data: { data: {}, object: 'list', type: 'text' } } as ReturnType<typeof useModelCompatibilityMapping>)
})

it('offers retry when the model catalog fails', () => {
  const refetch = jest.fn()
  mockUseModels.mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: true,
    refetch,
  } as unknown as ReturnType<typeof useModels>)

  render(<ModelsView />)
  expect(screen.getByRole('heading', { name: 'Could not load models' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
  expect(refetch).toHaveBeenCalledTimes(1)
})

it('clears filters from the empty state', () => {
  mockUseModels.mockReturnValue({
    data: { models: [{ id: 'zai-org-glm-5-2', type: 'text' }], count: 1, types: ['text'] },
    isLoading: false,
    isError: false,
    refetch: jest.fn(),
  } as unknown as ReturnType<typeof useModels>)

  render(<ModelsView />)
  fireEvent.change(screen.getByRole('textbox', { name: /search models, traits/i }), { target: { value: 'no-such-model' } })
  expect(screen.getByRole('heading', { name: 'No models match your filters' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Clear all filters' }))
  expect(screen.getByText('zai-org-glm-5-2')).toBeInTheDocument()
})