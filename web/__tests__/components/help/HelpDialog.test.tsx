import { fireEvent, render, screen } from '../../test-utils'
import { HELP_EVENT, HelpDialog } from '@/components/help/HelpDialog'

describe('HelpDialog', () => {
  it('opens with the ? keyboard shortcut and lists shortcuts and glossary', async () => {
    render(<HelpDialog />)
    fireEvent.keyDown(window, { key: '?' })

    expect(await screen.findByText('Keyboard shortcuts & glossary')).toBeInTheDocument()
    expect(screen.getByText('Ctrl/⌘ + K')).toBeInTheDocument()
    expect(screen.getByText('VVV')).toBeInTheDocument()
    expect(screen.getByText(/Daily inference credit/i)).toBeInTheDocument()
  })

  it('does not hijack ? typed into an input', async () => {
    render(
      <div>
        <input aria-label="text field" />
        <HelpDialog />
      </div>,
    )
    fireEvent.keyDown(screen.getByLabelText('text field'), { key: '?' })
    expect(screen.queryByText('Keyboard shortcuts & glossary')).not.toBeInTheDocument()
  })

  it('opens from the custom help event (command palette)', async () => {
    render(<HelpDialog />)
    fireEvent(window, new Event(HELP_EVENT))
    expect(await screen.findByText('Keyboard shortcuts & glossary')).toBeInTheDocument()
  })
})
