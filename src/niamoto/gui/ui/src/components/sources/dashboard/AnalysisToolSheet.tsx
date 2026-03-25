import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'

interface AnalysisToolSheetProps {
  open: boolean
  title?: string
  description?: string
  content?: React.ReactNode
  onOpenChange: (open: boolean) => void
}

export function AnalysisToolSheet({
  open,
  title,
  description,
  content,
  onOpenChange,
}: AnalysisToolSheetProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-[min(960px,92vw)] sm:max-w-[960px]">
        <SheetHeader className="px-6 pt-6">
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription>{description}</SheetDescription>
        </SheetHeader>
        <ScrollArea className="h-[calc(100vh-110px)] px-6 pb-6">
          <div className="pt-6">{content}</div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
