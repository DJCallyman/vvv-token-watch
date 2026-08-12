'use client'

import { useEffect, useState } from 'react'
import {
  ColumnDefinition,
  getColumnsForType,
  loadColumnPreferences,
  saveColumnPreferences,
  ModelType,
} from './columnConfig'
import { RotateCcw } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button, Dialog, DialogContent, DialogTitle } from '@/components/ui'

interface ColumnSelectorProps {
  isOpen: boolean
  onClose: () => void
  modelType: ModelType
  onColumnsChange?: (hiddenColumns: Set<string>) => void
}

export function ColumnSelector({ isOpen, onClose, modelType, onColumnsChange }: ColumnSelectorProps) {
  const [hiddenColumns, setHiddenColumns] = useState<Set<string>>(() => 
    loadColumnPreferences(modelType)
  )
  const allColumns = getColumnsForType(modelType)

  useEffect(() => {
    setHiddenColumns(loadColumnPreferences(modelType))
  }, [modelType])

  const toggleColumn = (key: string) => {
    if (key === 'model') return
    setHiddenColumns(prev => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      saveColumnPreferences(modelType, next)
      onColumnsChange?.(next)
      return next
    })
  }

  const resetToDefaults = () => {
    const empty = new Set<string>()
    setHiddenColumns(empty)
    saveColumnPreferences(modelType, empty)
    onColumnsChange?.(empty)
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="p-0">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <DialogTitle className="font-semibold">Select Columns</DialogTitle>
        </div>
        
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          <p className="text-sm text-muted-foreground mb-4">
            Toggle column visibility for {modelType === 'all' ? 'all types' : `${modelType} models`}
          </p>
          
          <div className="space-y-2">
            {allColumns.map((column) => {
              const isHidden = hiddenColumns.has(column.key)
              const isModelColumn = column.key === 'model'
              
              return (
                <label
                  key={column.key}
                  className={cn(
                    "flex items-center gap-3 p-2 rounded cursor-pointer transition-colors",
                    isModelColumn ? "opacity-50 cursor-not-allowed" : "hover:bg-muted"
                  )}
                >
                  <input
                    type="checkbox"
                    checked={!isHidden}
                    onChange={() => !isModelColumn && toggleColumn(column.key)}
                    disabled={isModelColumn}
                    className="w-4 h-4 rounded border-input"
                  />
                  <div className="flex-1">
                    <span className="text-sm font-medium">{column.header}</span>
                    {column.tooltip && (
                      <span className="text-xs text-muted-foreground ml-2">
                        ({column.tooltip})
                      </span>
                    )}
                  </div>
                </label>
              )
            })}
          </div>
        </div>
        
        <div className="flex items-center justify-between p-4 border-t border-border bg-muted/30">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={resetToDefaults}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset to Defaults
          </Button>
          <Button
            type="button"
            onClick={onClose}
          >
            Done
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
