import { fireEvent, render, screen } from '../../test-utils'
import { OnboardingChecklist } from '@/components/onboarding/OnboardingChecklist'

beforeEach(() => {
  window.localStorage.clear()
})

describe('OnboardingChecklist', () => {
  it('renders first-run guidance with progress', () => {
    render(<OnboardingChecklist />)
    expect(screen.getByText('Getting started')).toBeInTheDocument()
    expect(screen.getByText(/0\/4 complete/i)).toBeInTheDocument()
  })

  it('persists completed steps in localStorage and updates progress', () => {
    render(<OnboardingChecklist />)
    fireEvent.click(screen.getAllByRole('button', { name: /mark .* as done/i })[0])

    expect(screen.getByText(/1\/4 complete/i)).toBeInTheDocument()
    const stored = JSON.parse(window.localStorage.getItem('vvv:onboarding-progress') ?? '[]')
    expect(stored).toHaveLength(1)
  })

  it('stays dismissed across renders once dismissed', () => {
    const first = render(<OnboardingChecklist />)
    fireEvent.click(screen.getByRole('button', { name: /dismiss .* checklist/i }))
    expect(screen.queryByText('Getting started')).not.toBeInTheDocument()

    first.unmount()
    render(<OnboardingChecklist />)
    expect(screen.queryByText('Getting started')).not.toBeInTheDocument()
  })
})
