import { fireEvent, render, screen } from '../../test-utils'
import { DataState } from '@/components/ui/data-state'

describe('DataState', () => {
  it('announces loading and displays content-shaped placeholders', () => {
    render(<DataState kind="loading" title="Loading model catalog" rows={2} />)

    expect(screen.getByText('Loading model catalog').closest('[aria-live="polite"]')).toHaveAttribute('aria-busy', 'true')
    expect(screen.getByText('Loading model catalog')).toBeInTheDocument()
    expect(document.querySelectorAll('[aria-hidden="true"] .animate-pulse')).toHaveLength(4)
  })

  it('provides retry for errors', () => {
    const onRetry = jest.fn()
    render(<DataState kind="error" title="Unable to load prices" description="Check your connection." onRetry={onRetry} />)

    expect(screen.getByRole('alert')).toHaveTextContent('Check your connection.')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('renders an empty state action', () => {
    render(<DataState kind="empty" title="No results" action={<button type="button">Clear filters</button>} />)
    expect(screen.getByText('No results').closest('[aria-live="polite"]')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Clear filters' })).toBeInTheDocument()
  })

  it('labels retained query data as stale and offers retry', () => {
    const onRetry = jest.fn()
    render(<DataState kind="stale" title="Showing last available data" onRetry={onRetry} />)

    expect(screen.getByText('Showing last available data')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})