import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TraitsPanel } from '@/components/models/TraitsPanel'
import { useModelTraits } from '@/lib/hooks'

jest.mock('@/lib/hooks')

const mockUseModelTraits = useModelTraits as jest.MockedFunction<typeof useModelTraits>

describe('TraitsPanel — loading', () => {
  beforeEach(() => {
    mockUseModelTraits.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as any)
  })

  it('shows loading placeholder', () => {
    render(<TraitsPanel />)
    expect(screen.getByText(/Loading trait recommendations/i)).toBeInTheDocument()
  })
})

describe('TraitsPanel — error', () => {
  beforeEach(() => {
    mockUseModelTraits.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as any)
  })

  it('renders nothing on error (non-fatal)', () => {
    const { container } = render(<TraitsPanel />)
    expect(container.firstChild).toBeNull()
  })
})

describe('TraitsPanel — empty', () => {
  beforeEach(() => {
    mockUseModelTraits.mockReturnValue({
      data: { data: {}, object: 'list', type: 'text' },
      isLoading: false,
      isError: false,
    } as any)
  })

  it('renders nothing for empty trait map', () => {
    const { container } = render(<TraitsPanel />)
    expect(container.firstChild).toBeNull()
  })
})

describe('TraitsPanel — populated', () => {
  beforeEach(() => {
    mockUseModelTraits.mockReturnValue({
      data: {
        data: {
          default: 'zai-org-glm-5-1',
          fastest: 'kimi-k2-6',
          smartest: 'claude-opus-4-6',
        },
        object: 'list',
        type: 'text',
      },
      isLoading: false,
      isError: false,
    } as any)
  })

  it('renders header', () => {
    render(<TraitsPanel />)
    expect(screen.getByText(/Venice Recommended/i)).toBeInTheDocument()
  })

  it('renders one pill per trait', () => {
    render(<TraitsPanel />)
    expect(screen.getByText(/default/i)).toBeInTheDocument()
    expect(screen.getByText(/fastest/i)).toBeInTheDocument()
    expect(screen.getByText(/smartest/i)).toBeInTheDocument()
  })

  it('shows model id next to each trait', () => {
    render(<TraitsPanel />)
    expect(screen.getByText('zai-org-glm-5-1')).toBeInTheDocument()
    expect(screen.getByText('kimi-k2-6')).toBeInTheDocument()
  })

  it('shows the active model type in subtitle', () => {
    const { container } = render(<TraitsPanel modelType="text" />)
    const descriptionEl = container.querySelector('p[class*="text-muted-foreground"]')
    expect(descriptionEl?.textContent).toMatch(/Type:\s*text/i)
  })

  it('clicking a pill calls onPickModel with the model id', async () => {
    const user = userEvent.setup()
    const onPickModel = jest.fn()
    render(<TraitsPanel onPickModel={onPickModel} />)

    const buttons = screen.getAllByRole('button')
    const quickestBtn = buttons.find((b) => b.textContent?.includes('fastest')) as HTMLElement
    await user.click(quickestBtn)

    expect(onPickModel).toHaveBeenCalledWith('kimi-k2-6')
  })

  it('disables button when onPickModel is not provided', () => {
    render(<TraitsPanel />)
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
    buttons.forEach((b) => {
      expect(b).toBeDisabled()
    })
  })

  it('marks selected pill with aria-pressed', () => {
    render(<TraitsPanel selectedModelId="kimi-k2-6" onPickModel={() => {}} />)
    const fastestPill = screen.getAllByRole('button').find((b) =>
      b.textContent?.includes('fastest'),
    )
    expect(fastestPill).toHaveAttribute('aria-pressed', 'true')
  })

  it('other pills have aria-pressed=false', () => {
    render(<TraitsPanel selectedModelId="kimi-k2-6" onPickModel={() => {}} />)
    const defaultPill = screen.getAllByRole('button').find((b) =>
      b.textContent?.includes('default'),
    )
    expect(defaultPill).toHaveAttribute('aria-pressed', 'false')
  })
})

describe('TraitsPanel — filters out empty model ids', () => {
  beforeEach(() => {
    mockUseModelTraits.mockReturnValue({
      data: {
        data: {
          default: 'zai-org-glm-5-1',
          experimental: '',
          fastest: null,
        },
        object: 'list',
        type: 'text',
      },
      isLoading: false,
      isError: false,
    } as any)
  })

  it('only renders pills with non-empty model ids', () => {
    render(<TraitsPanel />)
    expect(screen.getByText(/default/i)).toBeInTheDocument()
    expect(screen.queryByText(/experimental/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/fastest/i)).not.toBeInTheDocument()
  })
})
