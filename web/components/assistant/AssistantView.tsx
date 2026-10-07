'use client'

import { useState } from 'react'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button, Input } from '@/components/ui'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'

export function AssistantView() {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)
  const submit = async (value = query) => {
    if (!value.trim() || loading) return
    setLoading(true)
    setAnswer('')
    try {
      setAnswer((await api.queryAssistant(value)).answer)
      toast.success('Assistant response ready')
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Assistant request failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Token Watch Assistant</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ask read-only questions about your Venice account and token data.
        </p>
      </div>
      <Card>
        <CardHeader><CardTitle>Ask a question</CardTitle></CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  void submit()
                }
              }}
              placeholder="How is my current usage trending?"
              className="min-w-0 flex-1"
              aria-label="Assistant question"
            />
            <Button onClick={() => { void submit() }} disabled={loading}>
              {loading ? 'Thinking…' : 'Ask'}
            </Button>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {['What is my current balance?', 'What are VVV and DIEM prices?', 'Summarize my usage'].map((prompt) => (
              <Button
                key={prompt}
                variant="outline"
                size="sm"
                disabled={loading}
                onClick={() => {
                  setQuery(prompt)
                  void submit(prompt)
                }}
              >
                {prompt}
              </Button>
            ))}
          </div>
          {loading && (
            <div aria-live="polite" aria-busy="true" className="mt-6 space-y-3 rounded-md bg-muted/50 p-4">
              <span className="sr-only">Generating assistant response</span>
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          )}
          {answer && (
            <div className="mt-6 rounded-md bg-muted/50 p-4 whitespace-pre-wrap text-sm leading-6" aria-live="polite">
              {answer}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
