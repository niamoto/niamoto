import { useTranslation } from 'react-i18next'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import { EnrichmentTab } from '@/features/import/components/enrichment/EnrichmentTab'
import type { ReferenceInfo } from '@/hooks/useReferences'

interface EnrichmentWorkspaceSheetProps {
  open: boolean
  reference: ReferenceInfo | null
  onOpenChange: (open: boolean) => void
  onConfigSaved?: () => void
}

export function EnrichmentWorkspaceSheet({
  open,
  reference,
  onOpenChange,
  onConfigSaved,
}: EnrichmentWorkspaceSheetProps) {
  const { t } = useTranslation('sources')

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-[min(1100px,96vw)] sm:max-w-[1100px] p-0"
      >
        <SheetHeader className="px-6 pt-6">
          <SheetTitle>
            {reference
              ? t('dashboard.enrichment.sheetTitle', {
                  name: reference.name,
                  defaultValue: `Enrichment · ${reference.name}`,
                })
              : t('dashboard.enrichment.sheetFallbackTitle', 'Enrichment')}
          </SheetTitle>
          <SheetDescription>
            {reference
              ? t(
                  'dashboard.enrichment.sheetDescription',
                  'Configure and run external enrichment without leaving the data workspace.'
                )
              : ''}
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-96px)]">
          <div className="px-6 pb-6 pt-2">
            {reference && (
              <EnrichmentTab
                referenceName={reference.name}
                hasEnrichment={Boolean(reference.enrichment_enabled)}
                onConfigSaved={onConfigSaved}
              />
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
