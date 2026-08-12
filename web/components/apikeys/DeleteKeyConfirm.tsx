'use client'

import { AlertTriangle } from 'lucide-react'
import type { APIKeyUsage } from '@/lib/api'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogTitle } from '@/components/ui/alert-dialog'

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
  return (
    <AlertDialog open onOpenChange={(open) => !open && !submitting && onCancel()}>
      <AlertDialogContent aria-labelledby="delete-title">
        <div className="w-full max-w-md rounded-lg border border-border bg-card shadow-lg">
        <div className="flex items-start gap-3 p-4">
          <div className="rounded-full bg-destructive/10 p-2 text-destructive">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="flex-1">
            <AlertDialogTitle id="delete-title" className="text-lg font-semibold">
              Delete API key?
            </AlertDialogTitle>
            <AlertDialogDescription className="mt-1">
              This will permanently revoke <span className="font-medium text-foreground">
                {apiKey.name}
              </span>
              . Any service using this key will stop working immediately. This
              action cannot be undone.
            </AlertDialogDescription>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t border-border p-4">
          <AlertDialogCancel
            type="button"
            disabled={submitting}
          >
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            type="button"
            onClick={onConfirm}
            disabled={submitting}
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
          >
            {submitting ? 'Deleting…' : 'Delete key'}
          </AlertDialogAction>
        </div>
      </div>
      </AlertDialogContent>
    </AlertDialog>
  )
}
