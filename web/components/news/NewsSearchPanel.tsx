'use client'

import { useState } from 'react'
import { useAskNews, useNewsSearch } from '@/lib/hooks'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Sparkles } from 'lucide-react'

export function NewsSearchPanel() {
  const search = useNewsSearch()
  const ask = useAskNews()
  const [query, setQuery] = useState('')
  const [question, setQuestion] = useState('')

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="w-5 h-5" aria-hidden="true" />
          Semantic Search &amp; Q&amp;A
        </CardTitle>
        <CardDescription>
          Embedding-ranked search over the cached news set, plus retrieval-augmented answers
          with cited sources.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <form
          className="flex flex-col sm:flex-row gap-3"
          onSubmit={(event) => {
            event.preventDefault()
            if (query.trim()) search.mutate({ query: query.trim(), topK: 5 })
          }}
        >
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search news semantically (e.g. staking incentives)"
            aria-label="Semantic news search query"
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={search.isPending || !query.trim()}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            {search.isPending ? 'Searching…' : 'Search'}
          </button>
        </form>

        {search.data && (
          <ul className="space-y-2">
            {search.data.results.length === 0 && (
              <li className="text-sm text-muted-foreground">No matching articles.</li>
            )}
            {search.data.results.map((result) => (
              <li key={`${result.url}-${result.title}`} className="rounded-md border border-border p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">{result.title}</p>
                  <span className="text-xs text-muted-foreground">score {result.score.toFixed(3)}</span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{result.snippet}</p>
              </li>
            ))}
          </ul>
        )}

        <form
          className="flex flex-col sm:flex-row gap-3"
          onSubmit={(event) => {
            event.preventDefault()
            if (question.trim()) ask.mutate({ question: question.trim(), topK: 5 })
          }}
        >
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask a question grounded in recent news"
            aria-label="Ask a question about the news"
            className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={ask.isPending || !question.trim()}
            className="rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-accent disabled:opacity-50"
          >
            {ask.isPending ? 'Answering…' : 'Ask'}
          </button>
        </form>

        {ask.data && (
          <div className="rounded-md border border-border p-4 space-y-2">
            <p className="whitespace-pre-wrap text-sm leading-6">{ask.data.answer}</p>
            {ask.data.sources.length > 0 && (
              <ul className="space-y-1">
                {ask.data.sources.map((source) => (
                  <li key={source}>
                    <a
                      href={source}
                      target="_blank"
                      rel="noreferrer"
                      className="text-xs text-primary hover:underline"
                    >
                      {source}
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
