import { fireEvent, render, screen, waitFor } from '../../test-utils'
import { DocumentView } from '@/components/documents/DocumentView'
import { api } from '@/lib/api'
import { useParseDocument } from '@/lib/hooks'

jest.mock('@/lib/hooks')
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }))

const mockUseParseDocument = useParseDocument as jest.MockedFunction<typeof useParseDocument>

const parsed = {
  filename: 'whitepaper.pdf',
  format: 'pdf',
  input_kind: 'base64',
  characters: 1200,
  truncated: false,
  extracted_text: 'Tokenomics details here.',
  summary: 'A compact summary.',
  key_points: ['Point A'],
  risk_factors: ['Risk A'],
  model: 'm',
  note: 'verify',
}

const parse = { mutate: jest.fn(), isPending: false }

beforeEach(() => {
  jest.clearAllMocks()
  mockUseParseDocument.mockReturnValue(parse as any)
})

describe('DocumentView', () => {
  it('renders summary, key points, and risk factors', () => {
    render(<DocumentView />)
    // Simulate a completed parse by invoking the mutation success callback.
    parse.mutate.mockImplementation((_body, options) => options?.onSuccess?.(parsed))

    const file = new File(['hello'], 'notes.txt', { type: 'text/plain' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, { target: { files: [file] } })

    return waitFor(() => {
      expect(screen.getByText('A compact summary.')).toBeInTheDocument()
      expect(screen.getByText('Point A')).toBeInTheDocument()
      expect(screen.getByText('Risk A')).toBeInTheDocument()
    })
  })

  it('asks the parsed document a grounded question', async () => {
    parse.mutate.mockImplementation((_body, options) => options?.onSuccess?.(parsed))
    const ask = jest.spyOn(api, 'askDocument').mockResolvedValue({ answer: 'Grounded answer.' })

    render(<DocumentView />)
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, { target: { files: [new File(['hello'], 'notes.txt', { type: 'text/plain' })] } })
    await screen.findByText('A compact summary.')

    fireEvent.change(screen.getByLabelText('Question about the document'), {
      target: { value: 'What about tokenomics?' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }))

    await waitFor(() => expect(ask).toHaveBeenCalledWith('Tokenomics details here.', 'What about tokenomics?'))
    await waitFor(() => expect(screen.getByText('Grounded answer.')).toBeInTheDocument())
  })

  it('rejects files above the size limit', () => {
    render(<DocumentView />)
    const big = new File(['x'], 'big.pdf', { type: 'application/pdf' })
    Object.defineProperty(big, 'size', { value: 5_000_000 })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, { target: { files: [big] } })
    expect(parse.mutate).not.toHaveBeenCalled()
  })
})
