import { fireEvent, render, screen } from '../../test-utils'
import { SignalHistory } from '@/components/insights/SignalHistory'
import { useEvaluateSignal, useSignals } from '@/lib/hooks'

jest.mock('@/lib/hooks')

const mockUseSignals = useSignals as jest.MockedFunction<typeof useSignals>
const mockUseEvaluateSignal = useEvaluateSignal as jest.MockedFunction<typeof useEvaluateSignal>

const evaluate = { mutate: jest.fn(), isPending: false }

const signals = [
  {
    id: 1,
    kind: 'analysis',
    subject: 'vvv',
    direction: 'bullish',
    confidence: 72,
    rationale: 'Momentum improving.',
    sources: [],
    metrics: {},
    entry_price_usd: 1.5,
    outcome_status: 'pending',
    outcome_value_usd: null,
    outcome_note: null,
    evaluated_at: null,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 2,
    kind: 'x_sentiment',
    subject: 'vvv',
    direction: 'bearish',
    confidence: 55,
    rationale: 'Negative chatter.',
    sources: [],
    metrics: {},
    entry_price_usd: 2,
    outcome_status: 'hit',
    outcome_value_usd: 1.8,
    outcome_note: 'Move -10%',
    evaluated_at: '2026-01-02T00:00:00Z',
    created_at: '2026-01-01T00:00:00Z',
  },
]

beforeEach(() => {
  jest.clearAllMocks()
  mockUseSignals.mockReturnValue({ data: { signals, count: 2 }, isLoading: false, isError: false } as any)
  mockUseEvaluateSignal.mockReturnValue(evaluate as any)
})

describe('SignalHistory', () => {
  it('renders direction, confidence, and outcome badges', () => {
    render(<SignalHistory />)
    expect(screen.getByText('bullish')).toBeInTheDocument()
    expect(screen.getByText('bearish')).toBeInTheDocument()
    expect(screen.getByText('72% confidence')).toBeInTheDocument()
    expect(screen.getByText('Hit')).toBeInTheDocument()
    expect(screen.getByText('Pending')).toBeInTheDocument()
  })

  it('evaluates only pending signals and links event ids', () => {
    render(<SignalHistory />)
    fireEvent.click(screen.getByRole('button', { name: /evaluate outcome/i }))
    expect(evaluate.mutate).toHaveBeenCalledWith({ id: 1 })
    expect(screen.getAllByRole('button', { name: /evaluate outcome/i })).toHaveLength(1)
  })

  it('shows an empty state', () => {
    mockUseSignals.mockReturnValue({ data: { signals: [], count: 0 }, isLoading: false, isError: false } as any)
    render(<SignalHistory />)
    expect(screen.getByText(/no signals recorded yet/i)).toBeInTheDocument()
  })

  it('surfaces load failures', () => {
    mockUseSignals.mockReturnValue({ data: undefined, isLoading: false, isError: true } as any)
    render(<SignalHistory />)
    expect(screen.getByText(/failed to load signals/i)).toBeInTheDocument()
  })
})
