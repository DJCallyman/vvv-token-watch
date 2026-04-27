'use client'

import { useState } from 'react'

const TESTS = [
  { id: 'T1', name: 'Latency', desc: 'Time-to-first-token and throughput' },
  { id: 'T2', name: 'Tool Calling', desc: 'Function call with valid JSON arguments' },
  { id: 'T3', name: 'Structured Output', desc: 'JSON schema adherence (person record)' },
  { id: 'T4', name: 'Instruction Following', desc: 'Follow strict output format constraints' },
  { id: 'T5', name: 'Reasoning Quality', desc: 'Multi-step logic puzzle (river crossing)' },
  { id: 'T6', name: 'Context Coherence', desc: 'Multi-turn memory retention' },
  { id: 'T7', name: 'Consistency', desc: 'Same answer across repeated identical prompts' },
  { id: 'T8', name: 'Conciseness', desc: 'Response within a specified word limit' },
]

interface Props {
  selected: string[]
  onChange: (tests: string[]) => void
}

export function TestSelector({ selected, onChange }: Props) {
  const toggle = (id: string, checked: boolean) => {
    if (checked) {
      onChange([...selected, id])
    } else {
      onChange(selected.filter((t) => t !== id))
    }
  }

  const selectAll = () => onChange(TESTS.map((t) => t.id))
  const selectNone = () => onChange([])

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">Tests</span>
        <div className="flex gap-2">
          <button onClick={selectAll} className="text-xs text-primary hover:underline">All</button>
          <button onClick={selectNone} className="text-xs text-muted-foreground hover:underline">None</button>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {TESTS.map((t) => (
          <label key={t.id} className="flex items-start gap-2 cursor-pointer group rounded-md p-1.5 hover:bg-muted/20 transition-colors">
            <input
              type="checkbox"
              checked={selected.includes(t.id)}
              onChange={(e) => toggle(t.id, e.target.checked)}
              className="w-3.5 h-3.5 mt-0.5 rounded border-border accent-primary shrink-0"
            />
            <div className="min-w-0">
              <span className="text-xs font-medium text-foreground">
                <span className="text-muted-foreground mr-1">{t.id}</span>
                {t.name}
              </span>
              <p className="text-xs text-muted-foreground leading-tight mt-0.5 hidden sm:block">{t.desc}</p>
            </div>
          </label>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">{selected.length} of {TESTS.length} selected</p>
    </div>
  )
}
