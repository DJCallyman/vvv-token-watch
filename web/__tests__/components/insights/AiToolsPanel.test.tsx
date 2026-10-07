import { fireEvent, render, screen, waitFor } from '../../test-utils'
import { AiToolsPanel } from '@/components/insights/AiToolsPanel'
import { api } from '@/lib/api'
import {
  useAnalyzeXSentiment,
  useBriefing,
  useMarketInfographic,
  useVideoRecapStatus,
} from '@/lib/hooks'

jest.mock('@/lib/hooks')
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }))

const mockSentiment = useAnalyzeXSentiment as jest.MockedFunction<typeof useAnalyzeXSentiment>
const mockInfographic = useMarketInfographic as jest.MockedFunction<typeof useMarketInfographic>
const mockBriefing = useBriefing as jest.MockedFunction<typeof useBriefing>
const mockVideo = useVideoRecapStatus as jest.MockedFunction<typeof useVideoRecapStatus>

const sentiment = { mutate: jest.fn(), isPending: false, data: undefined as unknown }
const infographic = { mutate: jest.fn(), isPending: false, data: undefined as unknown }
const briefing = { mutate: jest.fn(), isPending: false, data: undefined as unknown }

beforeEach(() => {
  jest.clearAllMocks()
  sentiment.data = undefined
  infographic.data = undefined
  briefing.data = undefined
  mockSentiment.mockReturnValue(sentiment as any)
  mockInfographic.mockReturnValue(infographic as any)
  mockBriefing.mockReturnValue(briefing as any)
  mockVideo.mockReturnValue({ data: undefined } as any)
})

describe('AiToolsPanel', () => {
  it('triggers X sentiment analysis and renders the structured result', () => {
    const view = render(<AiToolsPanel analysis={null} />)
    fireEvent.click(screen.getByRole('button', { name: /analyze x sentiment/i }))
    expect(sentiment.mutate).toHaveBeenCalled()

    view.unmount()
    sentiment.data = {
      direction: 'bullish',
      confidence: 74,
      summary: 'Positive chatter.',
      drivers: [],
      posts: [{ title: 'p', url: 'https://x.com/1', snippet: '' }],
      sources: [],
      model: 'm',
      signal_id: 3,
      source: 'x',
      note: 'informational',
    }
    render(<AiToolsPanel analysis={null} />)
    expect(screen.getByText('Positive chatter.')).toBeInTheDocument()
    expect(screen.getByText(/1 post/)).toBeInTheDocument()
  })

  it('seeds infographic generation from the current analysis', () => {
    render(
      <AiToolsPanel
        analysis={{
          summary: 'Calm markets.',
          sentiment: 'neutral',
          key_events: ['Event'],
          risks: [],
          confidence: 60,
          sources: [],
        }}
      />,
    )
    fireEvent.click(screen.getByRole('button', { name: /generate infographic/i }))
    expect(infographic.mutate).toHaveBeenCalledWith({
      summary: 'Calm markets.',
      direction: 'neutral',
      confidence: 60,
      key_points: ['Event'],
    })
  })

  it('renders the spoken briefing with audio controls', () => {
    const view = render(<AiToolsPanel analysis={null} />)
    fireEvent.click(screen.getByRole('button', { name: /daily briefing/i }))
    expect(briefing.mutate).toHaveBeenCalled()

    view.unmount()
    briefing.data = {
      text: 'Good morning.',
      audio_b64: 'AAAA',
      mime: 'audio/mpeg',
      voice: 'af_sky',
      model: 'tts',
    }
    render(<AiToolsPanel analysis={null} />)
    expect(screen.getByText('Good morning.')).toBeInTheDocument()
    expect(document.querySelector('audio')).not.toBeNull()
  })

  it('queues a video recap and tracks its status', async () => {
    jest.spyOn(api, 'queueVideoRecap').mockResolvedValue({
      queue_id: 'q-1',
      model: 'wan',
      prompt: 'p',
      status: 'queued',
    })
    mockVideo.mockReturnValue({
      data: { queue_id: 'q-1', model: 'wan', status: 'pending' },
    } as any)

    render(<AiToolsPanel analysis={null} />)
    fireEvent.click(screen.getByRole('button', { name: /video recap/i }))

    await waitFor(() => expect(api.queueVideoRecap).toHaveBeenCalled())
    expect(await screen.findByText(/video recap status: pending/i)).toBeInTheDocument()
  })
})
