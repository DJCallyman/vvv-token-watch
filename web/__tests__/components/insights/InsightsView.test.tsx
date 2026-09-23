import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { InsightsView } from '@/components/insights/InsightsView'
import { api, type MarketDecisions } from '@/lib/api'
import { toast } from 'sonner'

jest.mock('@/lib/api', () => {
  const actual = jest.requireActual('@/lib/api')
  return { ...actual, api: { analyzeMarket: jest.fn() } }
})
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }))

const mockAnalyzeMarket = api.analyzeMarket as jest.MockedFunction<typeof api.analyzeMarket>

export const analysisFixture = {
  summary: 'Markets are calm.',
  sentiment: 'neutral',
  key_events: ['Event one'],
  risks: ['Risk one'],
  confidence: 62,
  sources: [],
}

export const decisionsFixture: MarketDecisions = {
  model: 'jev-latest',
  answers: {
    sentiment: {
      type: 'score',
      score: 1.72,
      legend: { '0': 'Bearish', '1': 'Neutral', '2': 'Bullish' },
      probabilities: { '0': 0.05, '1': 0.23, '2': 0.72 },
      confidence: 0.68,
    },
    is_high_risk: { type: 'noul', noul: 0.18 },
    market_phase: {
      type: 'choice',
      choice: 'accumulation',
      probabilities: { accumulation: 0.51, consolidation: 0.29, uptrend: 0.08, downtrend: 0.07, unclear: 0.05 },
      confidence: 0.44,
    },
    news_supports_bullish: { type: 'noul', noul: 0.61 },
  },
  usage: { input_tokens: 429, output_tokens: 73 },
}

beforeEach(() => {
  jest.clearAllMocks()
})

describe('InsightsView — decisions card', () => {
  it('renders typed judgment tiles when decisions are present', async () => {
    mockAnalyzeMarket.mockResolvedValue({ analysis: analysisFixture, articles: [], decisions: decisionsFixture })

    render(<InsightsView />)
    fireEvent.click(screen.getByRole('button', { name: /generate analysis/i }))

    await waitFor(() => {
      expect(screen.getByText('Typed Judgments')).toBeInTheDocument()
    })
    expect(screen.getByText('Sentiment')).toBeInTheDocument()
    expect(screen.getByText('Downside risk')).toBeInTheDocument()
    expect(screen.getByText('Market phase')).toBeInTheDocument()
    expect(screen.getByText('News check')).toBeInTheDocument()
    // Sentiment legend label from the score (appears in headline + distribution legend)
    expect(screen.getAllByText('Bullish').length).toBeGreaterThan(0)
    // Risk probability rendered as a percentage
    expect(screen.getAllByText('18%').length).toBeGreaterThan(0)
    // Chosen market phase (headline + option bar label)
    expect(screen.getAllByText('accumulation').length).toBeGreaterThan(0)
  })

  it('does not render the judgments card when decisions are null', async () => {
    mockAnalyzeMarket.mockResolvedValue({ analysis: analysisFixture, articles: [], decisions: null, decisions_status: 'unavailable' })

    render(<InsightsView />)
    fireEvent.click(screen.getByRole('button', { name: /generate analysis/i }))

    await waitFor(() => {
      expect(screen.getByText('Briefing')).toBeInTheDocument()
    })
    expect(screen.queryByText('Typed Judgments')).not.toBeInTheDocument()
    // Subtle unavailability hint is shown instead
    expect(screen.getByText(/typed judgments unavailable/i)).toBeInTheDocument()
  })

  it('shows chat briefing cards alongside decisions', async () => {
    mockAnalyzeMarket.mockResolvedValue({ analysis: analysisFixture, articles: [], decisions: decisionsFixture })

    render(<InsightsView />)
    fireEvent.click(screen.getByRole('button', { name: /generate analysis/i }))

    await waitFor(() => {
      expect(screen.getByText('Briefing')).toBeInTheDocument()
    })
    expect(screen.getByText('Confidence')).toBeInTheDocument()
    expect(screen.getByText('Markets are calm.')).toBeInTheDocument()
  })
})

describe('InsightsView — errors', () => {
  it('renders an error alert when the analysis call fails', async () => {
    mockAnalyzeMarket.mockRejectedValue(new Error('Analysis failed'))

    render(<InsightsView />)
    fireEvent.click(screen.getByRole('button', { name: /generate analysis/i }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
    expect(screen.getByText('Analysis failed')).toBeInTheDocument()
    expect(toast.error).toHaveBeenCalledWith('Analysis failed')
  })
})
