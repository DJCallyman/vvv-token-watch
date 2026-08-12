'use client'

import { useState } from 'react'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function AssistantView() {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)
  const submit = async (value = query) => { if (!value.trim()) return; setLoading(true); try { setAnswer((await api.queryAssistant(value)).answer) } finally { setLoading(false) } }
  return <div className="mx-auto max-w-3xl space-y-6"><div><h1 className="text-3xl font-bold">Token Watch Assistant</h1><p className="text-sm text-muted-foreground mt-1">Ask read-only questions about your Venice account and token data.</p></div><Card><CardHeader><CardTitle>Ask a question</CardTitle></CardHeader><CardContent><div className="flex gap-2"><input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submit()} placeholder="How is my current usage trending?" className="min-w-0 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm" /><button onClick={() => submit()} disabled={loading} className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground disabled:opacity-50">{loading ? 'Thinking…' : 'Ask'}</button></div><div className="mt-4 flex flex-wrap gap-2">{['What is my current balance?', 'What are VVV and DIEM prices?', 'Summarize my usage'].map((prompt) => <button key={prompt} onClick={() => { setQuery(prompt); submit(prompt) }} className="rounded-full border border-border px-3 py-1.5 text-xs hover:bg-accent">{prompt}</button>)}</div>{answer && <div className="mt-6 rounded-md bg-muted/50 p-4 whitespace-pre-wrap text-sm leading-6">{answer}</div>}</CardContent></Card></div>
}
