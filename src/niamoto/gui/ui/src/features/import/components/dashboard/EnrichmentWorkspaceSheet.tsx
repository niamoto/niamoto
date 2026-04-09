import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
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
  const navigate = useNavigate()

  const openWorkspace = (sourceId?: string) => {
    if (!reference) return
    onOpenChange(false)
    const searchParams = new URLSearchParams({ tab: 'enrichment' })
    if (sourceId) {
      searchParams.set('source', sourceId)
    }
    navigate(`/sources/reference/${encodeURIComponent(reference.name)}?${searchParams.toString()}`)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-[min(1040px,96vw)] sm:max-w-[1040px] p-0"
      >
        <SheetHeader className="border-b px-6 py-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
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
                      'dashboard.enrichment.quickSheetDescription',
                      'Quick panel for running and testing enrichment. Use the workspace for full configuration and results.'
                    )
                  : ''}
              </SheetDescription>
            </div>

          </div>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-92px)]">
          <div className="px-6 pb-6 pt-4">
            {reference && (
              <EnrichmentTab
                referenceName={reference.name}
                hasEnrichment={Boolean(reference.enrichment_enabled)}
                onConfigSaved={onConfigSaved}
                mode="quick"
                onOpenWorkspace={openWorkspace}
              />
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
