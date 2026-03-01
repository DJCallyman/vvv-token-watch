import React from 'react'
import { render, screen } from '@testing-library/react'
import { Badge } from '@/components/ui/badge'

describe('Badge', () => {
  it('renders children text', () => {
    render(<Badge>Active</Badge>)
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('renders with default variant by default', () => {
    const { container } = render(<Badge>default</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge).toBeInTheDocument()
  })

  it('renders success variant', () => {
    const { container } = render(<Badge variant="success">Live</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toMatch(/bg-green-500/)
  })

  it('renders secondary variant', () => {
    const { container } = render(<Badge variant="secondary">Inactive</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toMatch(/bg-secondary/)
  })

  it('renders destructive variant', () => {
    const { container } = render(<Badge variant="destructive">Error</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toMatch(/bg-destructive/)
  })

  it('renders outline variant', () => {
    const { container } = render(<Badge variant="outline">Tag</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toMatch(/text-foreground/)
  })

  it('applies custom className', () => {
    const { container } = render(<Badge className="my-custom">text</Badge>)
    const badge = container.firstChild as HTMLElement
    expect(badge.className).toContain('my-custom')
  })

  it('passes through additional HTML attributes', () => {
    render(<Badge data-testid="my-badge">test</Badge>)
    expect(screen.getByTestId('my-badge')).toBeInTheDocument()
  })
})
