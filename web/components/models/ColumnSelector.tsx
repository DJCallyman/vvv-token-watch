'use client'

import { useEffect, useState } from 'react'
import {
  ColumnDefinition,
  getColumnsForType,
  loadColumnPreferences,
  saveColumnPreferences,
  ModelType,
} from './columnConfig'
import { X, RotateCcw } from 'lucide-react'
import { cn } from '@/lib/utils'

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

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-background border border-border rounded-lg shadow-lg w-full max-w-md max-h-[80vh] overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h3 className="font-semibold">Select Columns</h3>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-muted transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
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
          <button
            onClick={resetToDefaults}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md hover:bg-muted transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset to Defaults
          </button>
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}