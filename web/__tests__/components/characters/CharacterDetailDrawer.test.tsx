import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { CharacterDetailDrawer } from '@/components/characters/CharacterDetailDrawer'
import type { Character } from '@/lib/api'

const ALAN: Character = {
  id: 'alan-id',
  name: 'Alan Watts',
  slug: 'alan-watts',
  description: 'British philosopher who interpreted Eastern thought.',
  tags: ['AlanWatts', 'Philosophy', 'Buddhism'],
  modelId: 'venice-uncensored-1-2',
  photoUrl: 'https://example.com/alan.jpg',
  shareUrl: 'https://venice.ai/c/alan-watts',
  adult: false,
  featured: true,
  webEnabled: true,
  author: 'k3x9q',
  createdAt: '2024-12-20T21:28:08.934Z',
  updatedAt: '2024-12-20T21:28:08.934Z',
  stats: {
    averageRating: 4.7,
    imports: 112,
    ratingCount: 24,
    ratingSum: 113,
    userRating: null,
  },
}

describe('CharacterDetailDrawer — null', () => {
  it('renders nothing when character is null', () => {
    const { container } = render(
      <CharacterDetailDrawer character={null} onClose={() => {}} />,
    )
    expect(container.firstChild).toBeNull()
  })
})

describe('CharacterDetailDrawer — populated', () => {
  it('renders drawer with name as title', () => {
    render(<CharacterDetailDrawer character={ALAN} onClose={() => {}} />)
    expect(screen.getByRole('dialog', { name: /alan watts/i })).toBeInTheDocument()
  })

  it('renders description', () => {
    render(<CharacterDetailDrawer character={ALAN} onClose={() => {}} />)
    expect(screen.getByText(/British philosopher/i)).toBeInTheDocument()
  })

  it('renders all tags', () => {
    render(<CharacterDetailDrawer character={ALAN} onClose={() => {}} />)
    expect(screen.getByText('#AlanWatts')).toBeInTheDocument()
    expect(screen.getByText('#Philosophy')).toBeInTheDocument()
    expect(screen.getByText('#Buddhism')).toBeInTheDocument()
  })

  it('renders stats grid', () => {
    render(<CharacterDetailDrawer character={ALAN} onClose={() => {}} />)
    expect(screen.getByText('4.7')).toBeInTheDocument()
    expect(screen.getByText('112')).toBeInTheDocument()
    expect(screen.getAllByText('24').length).toBeGreaterThan(0)
  })

  it('renders model id', () => {
    render(<CharacterDetailDrawer character={ALAN} onClose={() => {}} />)
    expect(screen.getByText('venice-uncensored-1-2')).toBeInTheDocument()
  })

  it('renders author', () => {
    render(<CharacterDetailDrawer character={ALAN} onClose={() => {}} />)
    expect(screen.getByText('k3x9q')).toBeInTheDocument()
  })

  it('renders share URL link', () => {
    render(<CharacterDetailDrawer character={ALAN} onClose={() => {}} />)
    const link = screen.getByRole('link', { name: /open on venice/i })
    expect(link).toHaveAttribute('href', 'https://venice.ai/c/alan-watts')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('renders Featured badge when featured', () => {
    render(<CharacterDetailDrawer character={ALAN} onClose={() => {}} />)
    expect(screen.getByText('Featured')).toBeInTheDocument()
  })

  it('does not render adult badge for non-adult character', () => {
    render(<CharacterDetailDrawer character={ALAN} onClose={() => {}} />)
    expect(screen.queryByText(/adult \(18\+/i)).not.toBeInTheDocument()
  })

  it('renders adult badge when adult=true', () => {
    const adultChar: Character = { ...ALAN, adult: true }
    render(<CharacterDetailDrawer character={adultChar} onClose={() => {}} />)
    expect(screen.getByText(/adult \(18\+/i)).toBeInTheDocument()
  })

  it('shows italicized placeholder when description is null', () => {
    const noDesc: Character = { ...ALAN, description: null }
    render(<CharacterDetailDrawer character={noDesc} onClose={() => {}} />)
    expect(screen.getByText(/no description/i)).toBeInTheDocument()
  })
})

describe('CharacterDetailDrawer — interactions', () => {
  it('calls onClose when X button clicked', () => {
    const onClose = jest.fn()
    render(<CharacterDetailDrawer character={ALAN} onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: /close drawer/i }))
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onClose when Escape pressed', () => {
    const onClose = jest.fn()
    render(<CharacterDetailDrawer character={ALAN} onClose={onClose} />)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onClose when backdrop clicked', () => {
    const onClose = jest.fn()
    render(<CharacterDetailDrawer character={ALAN} onClose={onClose} />)
    // The dialog role wrapper handles the backdrop click.
    fireEvent.click(screen.getByRole('dialog'))
    expect(onClose).toHaveBeenCalled()
  })

  it('does not close when content area clicked (stopPropagation)', () => {
    const onClose = jest.fn()
    render(<CharacterDetailDrawer character={ALAN} onClose={onClose} />)
    // The inner panel stops propagation, so clicking the title text doesn't close.
    fireEvent.click(screen.getByRole('heading', { level: 2 }))
    expect(onClose).not.toHaveBeenCalled()
  })
})
