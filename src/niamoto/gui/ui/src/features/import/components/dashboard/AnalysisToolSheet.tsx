import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'

interface AnalysisToolNavItem {
  key: string
  title: string
}

interface AnalysisToolSheetProps {
  open: boolean
  title?: string
  description?: string
  content?: React.ReactNode
  tools?: AnalysisToolNavItem[]
  activeTool?: string | null
  onSelectTool?: (toolKey: string) => void
  onOpenChange: (open: boolean) => void
}

export function AnalysisToolSheet({
  open,
  title,
  description,
  content,
  tools = [],
  activeTool = null,
  onSelectTool,
  onOpenChange,
}: AnalysisToolSheetProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[min(960px,92vw)] sm:max-w-[960px]">
        <SheetHeader className="px-6 pt-6">
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription>{description}</SheetDescription>
        </SheetHeader>
        {tools.length > 0 && onSelectTool && (
          <div className="border-b px-6 pb-4">
            <div className="flex flex-wrap gap-2">
              {tools.map((tool) => (
                <Button
                  key={tool.key}
                  variant={activeTool === tool.key ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => onSelectTool(tool.key)}
                >
                  {tool.title}
                </Button>
              ))}
            </div>
          </div>
        )}
        <ScrollArea className="h-[calc(100vh-160px)] px-6 pb-6">
          <div className="pt-6">{content}</div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
