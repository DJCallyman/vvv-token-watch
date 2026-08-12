'use client'

import { useState } from 'react'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button, Input } from '@/components/ui'
import { toast } from 'sonner'

export function AssistantView() {
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(false)
   const submit = async (value = query) => { if (!value.trim()) return; setLoading(true); try { setAnswer((await api.queryAssistant(value)).answer) } catch (error) { toast.error(error instanceof Error ? error.message : 'Assistant request failed') } finally { setLoading(false) } }
   return <div className="mx-auto max-w-3xl space-y-6"><div><h1 className="text-3xl font-bold">Token Watch Assistant</h1><p className="text-sm text-muted-foreground mt-1">Ask read-only questions about your Venice account and token data.</p></div><Card><CardHeader><CardTitle>Ask a question</CardTitle></CardHeader><CardContent><div className="flex gap-2"><Input value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submit()} placeholder="How is my current usage trending?" className="min-w-0 flex-1" aria-label="Assistant question" /><Button onClick={() => submit()} disabled={loading}>{loading ? 'Thinking…' : 'Ask'}</Button></div><div className="mt-4 flex flex-wrap gap-2">{['What is my current balance?', 'What are VVV and DIEM prices?', 'Summarize my usage'].map((prompt) => <Button key={prompt} variant="outline" size="sm" onClick={() => { setQuery(prompt); submit(prompt) }}>{prompt}</Button>)}</div>{answer && <div className="mt-6 rounded-md bg-muted/50 p-4 whitespace-pre-wrap text-sm leading-6" aria-live="polite">{answer}</div>}</CardContent></Card></div>
}
