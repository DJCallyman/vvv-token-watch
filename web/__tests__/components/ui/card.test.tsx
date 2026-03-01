import React from 'react'
import { render, screen } from '@testing-library/react'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '@/components/ui/card'

describe('Card', () => {
  it('renders children', () => {
    render(<Card>card body</Card>)
    expect(screen.getByText('card body')).toBeInTheDocument()
  })

  it('applies rounded border classes', () => {
    const { container } = render(<Card>x</Card>)
    expect(container.firstChild).toHaveClass('rounded-lg')
  })

  it('accepts custom className', () => {
    const { container } = render(<Card className="w-full">x</Card>)
    expect(container.firstChild).toHaveClass('w-full')
  })
})

describe('CardHeader', () => {
  it('renders children', () => {
    render(<CardHeader>header content</CardHeader>)
    expect(screen.getByText('header content')).toBeInTheDocument()
  })

  it('applies flex layout class', () => {
    const { container } = render(<CardHeader>x</CardHeader>)
    expect(container.firstChild).toHaveClass('flex')
  })
})

describe('CardTitle', () => {
  it('renders as an h3 element', () => {
    render(<CardTitle>My Title</CardTitle>)
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('My Title')
  })

  it('applies semibold text class', () => {
    const { container } = render(<CardTitle>t</CardTitle>)
    expect(container.firstChild).toHaveClass('font-semibold')
  })
})

describe('CardDescription', () => {
  it('renders as a paragraph', () => {
    render(<CardDescription>A description here</CardDescription>)
    expect(screen.getByText('A description here')).toBeInTheDocument()
  })

  it('applies muted text class', () => {
    const { container } = render(<CardDescription>d</CardDescription>)
    expect(container.firstChild).toHaveClass('text-muted-foreground')
  })
})

describe('CardContent', () => {
  it('renders children', () => {
    render(<CardContent>content area</CardContent>)
    expect(screen.getByText('content area')).toBeInTheDocument()
  })
})

describe('CardFooter', () => {
  it('renders children', () => {
    render(<CardFooter>footer text</CardFooter>)
    expect(screen.getByText('footer text')).toBeInTheDocument()
  })

  it('applies flex items-center class', () => {
    const { container } = render(<CardFooter>f</CardFooter>)
    expect(container.firstChild).toHaveClass('flex', 'items-center')
  })
})

describe('Card composition', () => {
  it('renders a full card with all sub-components', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Full Card</CardTitle>
          <CardDescription>Card subtitle</CardDescription>
        </CardHeader>
        <CardContent>Main content</CardContent>
        <CardFooter>Footer action</CardFooter>
      </Card>
    )

    expect(screen.getByText('Full Card')).toBeInTheDocument()
    expect(screen.getByText('Card subtitle')).toBeInTheDocument()
    expect(screen.getByText('Main content')).toBeInTheDocument()
    expect(screen.getByText('Footer action')).toBeInTheDocument()
  })
})
