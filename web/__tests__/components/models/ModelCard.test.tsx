import React from 'react'
import userEvent from '@testing-library/user-event'
import { render, screen } from '../../test-utils'
import { ModelCard } from '@/components/models/ModelCard'

const cachedTextModel = {
  id: 'cached-text-model',
  type: 'text',
  supports_cache: true,
  model_spec: {
    pricing: {
      input: { usd: 1 },
      output: { usd: 2 },
      cache_input: { usd: 0.1 },
    },
  },
}

const musicModel = {
  id: 'music-model',
  type: 'music',
  supports_cache: true,
  model_spec: {
    pricing: {
      input: { usd: 1 },
      cache_input: { usd: 0.1 },
    },
  },
}

describe('ModelCard cache context', () => {
  it('shows cache savings for eligible text models', async () => {
    const user = userEvent.setup()
    render(<ModelCard model={cachedTextModel} />)

    await user.click(screen.getByRole('button', { name: /show details/i }))

    expect(screen.getByText('$0.10 / 1M')).toBeInTheDocument()
    expect(screen.getByText('90.0% below input')).toBeInTheDocument()
  })

  it('does not show text cache guidance for music models', async () => {
    const user = userEvent.setup()
    render(<ModelCard model={musicModel} />)

    await user.click(screen.getByRole('button', { name: /show details/i }))

    expect(screen.queryByText(/below input/i)).not.toBeInTheDocument()
  })
})
