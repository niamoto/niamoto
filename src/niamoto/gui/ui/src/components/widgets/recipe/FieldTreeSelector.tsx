import { useState, useMemo, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronRight, ChevronDown, Search, ChevronsUpDown } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import type { ColumnNode } from '@/lib/api/recipes'

interface FieldTreeSelectorProps {
  columns: ColumnNode[]
  value: string
  onChange: (path: string) => void
  placeholder?: string
  disabled?: boolean
  loading?: boolean
}

interface TreeNodeProps {
  node: ColumnNode
  depth: number
  selectedPath: string
  onSelect: (path: string) => void
  searchTerm: string
  expandedNodes: Set<string>
  onToggleExpand: (path: string) => void
}

function TreeNode({
  node,
  depth,
  selectedPath,
  onSelect,
  searchTerm,
  expandedNodes,
  onToggleExpand,
}: TreeNodeProps) {
  const hasChildren = node.children && node.children.length > 0
  const isExpanded = expandedNodes.has(node.path)
  const isSelected = selectedPath === node.path

  // Check if this node or any children match the search
  const matchesSearch = useMemo(() => {
    if (!searchTerm) return true
    const term = searchTerm.toLowerCase()
    if (node.name.toLowerCase().includes(term)) return true
    if (node.path.toLowerCase().includes(term)) return true
    // Check children recursively
    const checkChildren = (children: ColumnNode[]): boolean => {
      for (const child of children) {
        if (child.name.toLowerCase().includes(term)) return true
        if (child.path.toLowerCase().includes(term)) return true
        if (child.children && checkChildren(child.children)) return true
      }
      return false
    }
    if (hasChildren && checkChildren(node.children)) return true
    return false
  }, [node, searchTerm, hasChildren])

  if (!matchesSearch) return null

  return (
    <div>
      <div
        className={cn(
          'flex items-center gap-1 px-2 py-1.5 rounded cursor-pointer text-sm',
          'hover:bg-muted/50 transition-colors',
          isSelected && 'bg-primary/10 text-primary font-medium',
          depth > 0 && 'ml-4'
        )}
        onClick={() => {
          if (hasChildren) {
            onToggleExpand(node.path)
          } else {
            onSelect(node.path)
          }
        }}
      >
        {/* Expand/collapse icon for nodes with children */}
        {hasChildren ? (
          <button
            onClick={(e) => {
              e.stopPropagation()
              onToggleExpand(node.path)
            }}
            className="p-0.5 hover:bg-muted rounded"
          >
            {isExpanded ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
          </button>
        ) : (
          <span className="w-4" /> // Spacer for alignment
        )}

        {/* Node name */}
        <span className="flex-1 truncate">{node.name}</span>

        {/* Type badge */}
        <span className="text-xs text-muted-foreground px-1 py-0.5 rounded bg-muted">
          {node.type}
        </span>
      </div>

      {/* Children (if expanded) */}
      {hasChildren && isExpanded && (
        <div className="border-l border-muted ml-3 pl-1">
          {node.children.map((child) => (
            <TreeNode
              key={child.path}
              node={child}
              depth={depth + 1}
              selectedPath={selectedPath}
              onSelect={onSelect}
              searchTerm={searchTerm}
              expandedNodes={expandedNodes}
              onToggleExpand={onToggleExpand}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function FieldTreeSelector({
  columns,
  value,
  onChange,
  placeholder,
  disabled = false,
  loading = false,
}: FieldTreeSelectorProps) {
  const { t } = useTranslation('common')
  const [open, setOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(() => {
    // Auto-expand parent nodes if value is nested
    const expanded = new Set<string>()
    if (value && value.includes('.')) {
      const parts = value.split('.')
      let path = ''
      for (let i = 0; i < parts.length - 1; i++) {
        path = path ? `${path}.${parts[i]}` : parts[i]
        expanded.add(path)
      }
    }
    return expanded
  })

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [open])

  const handleToggleExpand = (path: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  const handleSelect = (path: string) => {
    onChange(path)
    setOpen(false)
    setSearchTerm('')
  }

  // Find the display name for the current value
  const displayValue = useMemo(() => {
    if (!value) return null
    return value
  }, [value])

  return (
    <div ref={containerRef} className="relative">
      <Button
        type="button"
        variant="outline"
        role="combobox"
        aria-expanded={open}
        disabled={disabled || loading}
        onClick={() => setOpen(!open)}
        className={cn(
          'w-full justify-between h-8 font-normal',
          !value && 'text-muted-foreground'
        )}
      >
        <span className="truncate">
          {loading ? t('status.loading') : displayValue || placeholder || t('messages.selectField')}
        </span>
        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
      </Button>

      {open && (
        <div className="absolute z-50 mt-1 w-[300px] rounded-md border bg-popover shadow-md">
          {/* Search input */}
          <div className="p-2 border-b">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={t('placeholders.search')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="h-8 pl-8"
                autoFocus
              />
            </div>
          </div>

          {/* Tree view */}
          <ScrollArea className="h-[250px]">
            <div className="p-2">
              {columns.length === 0 ? (
                <div className="text-sm text-muted-foreground text-center py-4">
                  {t('status.noFieldsAvailable')}
                </div>
              ) : (
                columns.map((column) => (
                  <TreeNode
                    key={column.path}
                    node={column}
                    depth={0}
                    selectedPath={value}
                    onSelect={handleSelect}
                    searchTerm={searchTerm}
                    expandedNodes={expandedNodes}
                    onToggleExpand={handleToggleExpand}
                  />
                ))
              )}
            </div>
          </ScrollArea>
        </div>
      )}
    </div>
  )
}
