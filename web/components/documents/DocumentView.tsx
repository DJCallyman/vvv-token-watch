'use client'

import { useRef, useState } from 'react'
import { api, type DocumentParseResponse } from '@/lib/api'
import { useParseDocument } from '@/lib/hooks'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'
import { FileText, Upload } from 'lucide-react'

const MAX_BYTES = 4_000_000

function readFileBuffer(file: File): Promise<ArrayBuffer> {
  if (typeof file.arrayBuffer === 'function') return file.arrayBuffer()
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as ArrayBuffer)
    reader.onerror = () => reject(reader.error ?? new Error('Could not read the file'))
    reader.readAsArrayBuffer(file)
  })
}

export function DocumentView() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [result, setResult] = useState<DocumentParseResponse | null>(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<string | null>(null)
  const [asking, setAsking] = useState(false)
  const parse = useParseDocument()

  const onFile = async (file: File) => {
    setAnswer(null)
    setResult(null)
    if (file.size > MAX_BYTES) {
      toast.error('Document exceeds the 4MB limit')
      return
    }
    const buffer = await readFileBuffer(file)
    let binary = ''
    const bytes = new Uint8Array(buffer)
    const chunk = 0x8000
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode(...bytes.subarray(i, i + chunk))
    }
    const contentBase64 = window.btoa(binary)
    parse.mutate(
      { filename: file.name, content_base64: contentBase64 },
      { onSuccess: (data) => setResult(data) },
    )
  }

  const onAsk = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!result || !question.trim()) return
    setAsking(true)
    try {
      const response = await api.askDocument(result.extracted_text, question.trim())
      setAnswer(response.answer)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Question failed')
    } finally {
      setAsking(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Documents</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Parse whitepapers, reports, and notes (PDF, Markdown, text, JSON) with Venice chat
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="w-5 h-5" aria-hidden="true" />
            Upload Document
          </CardTitle>
          <CardDescription>
            Documents are parsed in-request and summarized. Nothing is persisted by this app.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.md,.markdown,.txt,.json"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) void onFile(file)
              event.target.value = ''
            }}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={parse.isPending}
            className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            <FileText className="w-4 h-4" aria-hidden="true" />
            {parse.isPending ? 'Parsing…' : 'Choose file'}
          </button>
          {parse.isPending && <Skeleton className="h-32 w-full" aria-label="Parsing document" />}
        </CardContent>
      </Card>

      {result && (
        <div className="grid gap-6 lg:grid-cols-3">
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>{result.filename}</CardTitle>
              <CardDescription>
                {result.format} · {result.characters.toLocaleString()} characters
                {result.truncated ? ' · truncated for analysis' : ''}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="leading-7">{result.summary}</p>
              {result.key_points.length > 0 && (
                <>
                  <h2 className="font-semibold">Key points</h2>
                  <ul className="list-disc space-y-1 pl-5 text-sm">
                    {result.key_points.map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                </>
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Risk factors</CardTitle>
            </CardHeader>
            <CardContent>
              {result.risk_factors.length === 0 ? (
                <p className="text-sm text-muted-foreground">None identified.</p>
              ) : (
                <ul className="list-disc space-y-1 pl-5 text-sm">
                  {result.risk_factors.map((risk) => (
                    <li key={risk}>{risk}</li>
                  ))}
                </ul>
              )}
              <p className="mt-4 text-xs text-muted-foreground">{result.note}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Ask the Document</CardTitle>
            <CardDescription>Answers are grounded in the parsed text only.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <form onSubmit={onAsk} className="flex flex-col sm:flex-row gap-3">
              <input
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="What does the document say about tokenomics?"
                aria-label="Question about the document"
                className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
              <button
                type="submit"
                disabled={asking || !question.trim()}
                className="rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-accent disabled:opacity-50"
              >
                {asking ? 'Answering…' : 'Ask'}
              </button>
            </form>
            {answer && (
              <p className="whitespace-pre-wrap rounded-md border border-border p-4 text-sm leading-6">
                {answer}
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
