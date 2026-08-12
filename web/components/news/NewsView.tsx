'use client'

import { useState } from 'react'
import { useNews, useNewsArticle } from '@/lib/hooks'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button, Dialog, DialogContent, DialogTitle } from '@/components/ui'
import { RefreshCw, ExternalLink } from 'lucide-react'
import { api } from '@/lib/api'

export function NewsView() {
  const { data, isLoading, isError, refetch } = useNews()
  const [selected, setSelected] = useState<string | null>(null)
  const article = useNewsArticle(selected)
  return <div className="space-y-6">
    <div className="flex items-center justify-between"><div><h1 className="text-3xl font-bold">Token News</h1><p className="text-sm text-muted-foreground mt-1">Fresh VVV and DIEM context from Venice web search</p></div><button onClick={() => refetch()} className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm hover:bg-accent"><RefreshCw className="w-4 h-4" /> Refresh</button></div>
    {isLoading && <p className="text-muted-foreground">Loading news…</p>}
     {isError && <p className="text-destructive" role="alert">Failed to load news.</p>}
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">{data?.articles.map((item) => <Card key={`${item.url}-${item.title}`}><CardHeader><CardTitle className="text-lg">{item.title}</CardTitle><CardDescription>{item.source || 'Web'}{item.date ? ` · ${item.date}` : ''}</CardDescription></CardHeader><CardContent><p className="text-sm text-muted-foreground line-clamp-3">{item.snippet}</p><div className="mt-4 flex gap-3">{item.url && <><button onClick={() => setSelected(item.url)} className="text-sm text-primary hover:underline">Read article</button><a href={item.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">Open source <ExternalLink className="w-3 h-3" /></a></>}</div></CardContent></Card>)}</div>
     <Dialog open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
       <DialogContent className="max-w-3xl">
         <DialogTitle>{article.data?.title || 'Article'}</DialogTitle>
         <div className="max-h-[70vh] overflow-y-auto">
           <pre className="whitespace-pre-wrap font-sans text-sm leading-6">
             {article.data?.content || (article.isLoading ? 'Loading article…' : 'Unable to load article.')}
           </pre>
         </div>
       </DialogContent>
     </Dialog>
  </div>
}
