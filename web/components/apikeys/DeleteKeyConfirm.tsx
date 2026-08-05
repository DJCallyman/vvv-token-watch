'use client'

import { useEffect } from 'react'
import { X, AlertTriangle } from 'lucide-react'
import type { APIKeyUsage } from '@/lib/api'

export interface DeleteKeyConfirmProps {
  apiKey: APIKeyUsage
  onCancel: () => void
  onConfirm: () => void
  submitting?: boolean
}

export function DeleteKeyConfirm({
  apiKey,
  onCancel,
  onConfirm,
  submitting,
}: DeleteKeyConfirmProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) onCancel()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onCancel, submitting])

  return (
    <div
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="delete-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4"
    >
      <div className="w-full max-w-md rounded-lg border border-border bg-card shadow-lg">
        <div className="flex items-start gap-3 p-4">
          <div className="rounded-full bg-destructive/10 p-2 text-destructive">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="flex-1">
            <h2 id="delete-title" className="text-lg font-semibold">
              Delete API key?
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              This will permanently revoke <span className="font-medium text-foreground">
                {apiKey.name}
              </span>
              . Any service using this key will stop working immediately. This
              action cannot be undone.
            </p>
          </div>
          <button
            type="button"
            onClick={onCancel}
            aria-label="Cancel"
            disabled={submitting}
            className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex justify-end gap-2 border-t border-border p-4">
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            className="rounded-md border border-border px-4 py-2 text-sm hover:bg-accent disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? 'Deleting…' : 'Delete key'}
          </button>
        </div>
      </div>
    </div>
  )
}
