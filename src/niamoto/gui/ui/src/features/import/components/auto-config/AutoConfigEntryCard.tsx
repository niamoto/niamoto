import { Button } from '@/components/ui/button'
import { ChevronDown, Pencil } from 'lucide-react'

interface AutoConfigEntryCardProps {
  name: string
  compactSummary: string
  isExpanded: boolean
  onToggle: () => void
  onEdit?: () => void
  icon: React.ReactNode
  badges?: React.ReactNode
  details: React.ReactNode
  className?: string
}

export function AutoConfigEntryCard({
  name,
  compactSummary,
  isExpanded,
  onToggle,
  onEdit,
  icon,
  badges,
  details,
  className,
}: AutoConfigEntryCardProps) {
  return (
    <div className={className}>
      <div className="flex items-start justify-between gap-3 p-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            {icon}
            <span className="font-medium">{name}</span>
            {badges}
          </div>
          <div className="mt-1 text-sm text-muted-foreground">{compactSummary}</div>
        </div>

        <div className="flex items-center gap-1">
          {onEdit && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 gap-1 px-2 text-xs"
              onClick={onEdit}
            >
              <Pencil className="h-3 w-3" />
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1 px-2 text-xs"
            onClick={onToggle}
          >
            <ChevronDown className={`h-3 w-3 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
          </Button>
        </div>
      </div>

      {isExpanded && <div className="border-t px-3 py-3">{details}</div>}
    </div>
  )
}
