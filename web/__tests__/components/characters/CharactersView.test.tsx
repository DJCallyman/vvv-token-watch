import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CharactersView } from '@/components/characters/CharactersView'
import { useCharacters } from '@/lib/hooks'
import type { Character, GetCharactersParams } from '@/lib/api'

jest.mock('@/lib/hooks')

const mockUseCharacters = useCharacters as jest.MockedFunction<
  typeof useCharacters
>

const SAMPLE_CHARACTERS: Character[] = [
  {
    id: 'id-1',
    name: 'Alan Watts',
    slug: 'alan-watts',
    description: 'British philosopher.',
    tags: ['AlanWatts', 'Philosophy'],
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
  },
  {
    id: 'id-2',
    name: 'Ada Lovelace',
    slug: 'ada-lovelace',
    description: 'Pioneering computer scientist.',
    tags: ['AdaLovelace', 'Science', 'History'],
    modelId: 'llama-3.3-70b',
    photoUrl: null,
    shareUrl: null,
    adult: false,
    featured: false,
    webEnabled: true,
    author: 'p3x9q',
    createdAt: '2024-12-20T21:28:08.934Z',
    updatedAt: '2024-12-20T21:28:08.934Z',
    stats: {
      averageRating: 4.5,
      imports: 80,
      ratingCount: 16,
      ratingSum: 72,
      userRating: null,
    },
  },
]

function setupChars(
  dataOverrides: Partial<{ characters: Character[] }> = {},
  opts: { isLoading?: boolean; isError?: boolean; mockImpl?: (...args: unknown[]) => unknown } = {},
) {
  mockUseCharacters.mockImplementation((params: GetCharactersParams = {}) => {
    if (opts.mockImpl) {
      return opts.mockImpl(params) as ReturnType<typeof useCharacters>
    }
    return {
      data: { data: dataOverrides.characters ?? SAMPLE_CHARACTERS, object: 'list' as const },
      isLoading: opts.isLoading ?? false,
      isError: opts.isError ?? false,
      refetch: jest.fn(),
      isFetching: false,
    } as ReturnType<typeof useCharacters>
  })
}

describe('CharactersView — loading', () => {
  beforeEach(() => {
    setupChars({}, { isLoading: true })
  })

  it('renders loading skeleton placeholders', () => {
    render(<CharactersView />)
    expect(screen.getByRole('heading', { name: /characters/i })).toBeInTheDocument()
    // 8 placeholders should be present
    const cards = document.querySelectorAll('[class*="animate-pulse"]')
    expect(cards.length).toBeGreaterThanOrEqual(8)
  })
})

describe('CharactersView — error', () => {
  beforeEach(() => {
    setupChars({}, { isError: true })
  })

  it('renders error card', () => {
    render(<CharactersView />)
    expect(screen.getByText(/failed to load characters/i)).toBeInTheDocument()
  })
})

describe('CharactersView — populated', () => {
  beforeEach(() => {
    setupChars()
  })

  it('renders header with preview API badge', () => {
    render(<CharactersView />)
    expect(screen.getByRole('heading', { name: /characters/i })).toBeInTheDocument()
    expect(screen.getByText(/preview api/i)).toBeInTheDocument()
  })

  it('renders all character names', () => {
    render(<CharactersView />)
    expect(screen.getByText('Alan Watts')).toBeInTheDocument()
    expect(screen.getByText('Ada Lovelace')).toBeInTheDocument()
  })

  it('emits search param when typing (with debounce)', async () => {
    const user = userEvent.setup()
    render(<CharactersView />)
    const input = screen.getByPlaceholderText(/search by name/i)
    await user.type(input, 'alan')
    await waitFor(
      () => {
        const lastCall = mockUseCharacters.mock.calls.at(-1)?.[0]
        expect(lastCall?.search).toBe('alan')
      },
      { timeout: 1000 },
    )
  })

  it('changes sortBy when selecting dropdown', async () => {
    const user = userEvent.setup()
    render(<CharactersView />)
    await user.selectOptions(screen.getByLabelText(/sort by/i), 'highestRating')
    expect(mockUseCharacters.mock.calls.at(-1)?.[0]?.sortBy).toBe('highestRating')
  })

  it('opens detail drawer when card clicked', async () => {
    const user = userEvent.setup()
    render(<CharactersView />)
    await user.click(screen.getByRole('button', { name: /open character alan watts/i }))
    expect(screen.getByRole('dialog', { name: /alan watts/i })).toBeInTheDocument()
  })

  it('closes drawer when Escape pressed', async () => {
    const user = userEvent.setup()
    render(<CharactersView />)
    await user.click(screen.getByRole('button', { name: /open character alan watts/i }))
    expect(screen.getByRole('dialog', { name: /alan watts/i })).toBeInTheDocument()
    await user.keyboard('{Escape}')
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: /alan watts/i })).not.toBeInTheDocument()
    })
  })
})

describe('CharactersView — derived state', () => {
  it('shows tag pills from current results', () => {
    setupChars()
    render(<CharactersView />)
    expect(screen.getByRole('button', { name: /^#Philosophy$/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^#Science$/ })).toBeInTheDocument()
  })

  it('toggles web-only filter chip', async () => {
    const user = userEvent.setup()
    setupChars()
    render(<CharactersView />)
    const chip = screen.getByRole('button', { name: /web enabled only/i })
    await user.click(chip)
    expect(mockUseCharacters.mock.calls.at(-1)?.[0]?.isWebEnabled).toBe('true')
  })

  it('toggles include-adult filter chip', async () => {
    const user = userEvent.setup()
    setupChars()
    render(<CharactersView />)
    const chip = screen.getByRole('button', { name: /include adult/i })
    await user.click(chip)
    expect(mockUseCharacters.mock.calls.at(-1)?.[0]?.isAdult).toBe('true')
  })
})

describe('CharactersView — empty state', () => {
  beforeEach(() => {
    setupChars({ characters: [] })
  })

  it('shows empty state when no results', () => {
    render(<CharactersView />)
    expect(screen.getByText(/no characters match your filters/i)).toBeInTheDocument()
  })
})
