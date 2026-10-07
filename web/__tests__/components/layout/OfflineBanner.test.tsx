import { act, fireEvent, render, screen } from '../../test-utils'
import { OfflineBanner } from '@/components/layout/OfflineBanner'

function setOnline(value: boolean) {
  Object.defineProperty(window.navigator, 'onLine', {
    writable: true,
    configurable: true,
    value,
  })
}

describe('OfflineBanner', () => {
  afterEach(() => setOnline(true))

  it('shows cached-data status when the browser goes offline', () => {
    render(<OfflineBanner />)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()

    act(() => {
      setOnline(false)
      window.dispatchEvent(new Event('offline'))
    })
    expect(screen.getByRole('status')).toHaveTextContent(/offline — showing the last known data/i)
  })

  it('hides again when the connection returns', () => {
    render(<OfflineBanner />)
    act(() => {
      setOnline(false)
      window.dispatchEvent(new Event('offline'))
    })
    expect(screen.getByRole('status')).toBeInTheDocument()

    act(() => {
      setOnline(true)
      window.dispatchEvent(new Event('online'))
    })
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('offers a retry action', () => {
    render(<OfflineBanner />)
    act(() => {
      setOnline(false)
      window.dispatchEvent(new Event('offline'))
    })
    fireEvent.click(screen.getByRole('button', { name: /retry now/i }))
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})
