import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { CharacterCard } from '@/components/characters/CharacterCard'
import type { Character } from '@/lib/api'

const ALAN: Character = {
  id: 'alan-id',
  name: 'Alan Watts',
  slug: 'alan-watts',
  description: 'British philosopher who interpreted Eastern thought.',
  tags: ['AlanWatts', 'Philosophy', 'Buddhism', 'Wisdom'],
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

describe('CharacterCard', () => {
  it('renders name and slug', () => {
    render(<CharacterCard character={ALAN} />)
    expect(screen.getByText('Alan Watts')).toBeInTheDocument()
    expect(screen.getByText('/alan-watts')).toBeInTheDocument()
  })

  it('renders description when provided', () => {
    render(<CharacterCard character={ALAN} />)
    expect(screen.getByText(/British philosopher/i)).toBeInTheDocument()
  })

  it('renders rating summary', () => {
    render(<CharacterCard character={ALAN} />)
    expect(screen.getByText('4.7')).toBeInTheDocument()
  })

  it('renders imports count', () => {
    render(<CharacterCard character={ALAN} />)
    expect(screen.getByText('112')).toBeInTheDocument()
  })

  it('renders model id footer', () => {
    render(<CharacterCard character={ALAN} />)
    expect(screen.getByText('venice-uncensored-1-2')).toBeInTheDocument()
  })

  it('shows first 3 tags and a +N indicator', () => {
    render(<CharacterCard character={ALAN} />)
    expect(screen.getByText('#AlanWatts')).toBeInTheDocument()
    expect(screen.getByText('#Philosophy')).toBeInTheDocument()
    expect(screen.getByText('#Buddhism')).toBeInTheDocument()
    expect(screen.getByText('+1')).toBeInTheDocument()
  })

  it('renders the photo when photoUrl is provided', () => {
    render(<CharacterCard character={ALAN} />)
    const img = screen.getByAltText('Alan Watts')
    expect(img).toBeInTheDocument()
    expect(img.getAttribute('src')).toBe('https://example.com/alan.jpg')
  })

  it('renders initials placeholder when no photo', () => {
    const lucy: Character = { ...ALAN, photoUrl: null, name: 'Lucy Liu' }
    render(<CharacterCard character={lucy} />)
    const initials = screen.getByText('L')
    expect(initials).toBeInTheDocument()
    expect(screen.queryByAltText(/lucy liu/i)).not.toBeInTheDocument()
  })

  it('renders Featured badge when featured', () => {
    render(<CharacterCard character={ALAN} />)
    expect(screen.getByText('Featured')).toBeInTheDocument()
  })

  it('renders Adult badge when adult', () => {
    const adultChar: Character = { ...ALAN, adult: true }
    render(<CharacterCard character={adultChar} />)
    expect(screen.getByText('18+')).toBeInTheDocument()
  })

  it('renders Web off badge when webEnabled is false', () => {
    const webOff: Character = { ...ALAN, webEnabled: false }
    render(<CharacterCard character={webOff} />)
    expect(screen.getByText('Web off')).toBeInTheDocument()
  })

  it('calls onClick when clicked', () => {
    const onClick = jest.fn()
    render(<CharacterCard character={ALAN} onClick={onClick} />)
    fireEvent.click(screen.getByRole('button', { name: /open character alan watts/i }))
    expect(onClick).toHaveBeenCalledWith(ALAN)
  })

  it('calls onClick on Enter key', () => {
    const onClick = jest.fn()
    render(<CharacterCard character={ALAN} onClick={onClick} />)
    fireEvent.keyDown(screen.getByRole('button', { name: /open character alan watts/i }), {
      key: 'Enter',
    })
    expect(onClick).toHaveBeenCalledWith(ALAN)
  })

  it('calls onClick on Space key', () => {
    const onClick = jest.fn()
    render(<CharacterCard character={ALAN} onClick={onClick} />)
    fireEvent.keyDown(screen.getByRole('button', { name: /open character alan watts/i }), {
      key: ' ',
    })
    expect(onClick).toHaveBeenCalledWith(ALAN)
  })
})
