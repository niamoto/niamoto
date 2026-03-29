import { CheckCircle2, FolderUp, Sparkles } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { FileUploadZone } from '@/features/import/components/upload/FileUploadZone'
import type { UploadedFileInfo } from '@/features/import/api/upload'

interface SourcesEmptyStateProps {
  onFilesReady: (files: UploadedFileInfo[], paths: string[]) => void
  onOpenImportWorkspace: () => void
}

export function SourcesEmptyState({
  onFilesReady,
  onOpenImportWorkspace,
}: SourcesEmptyStateProps) {
  const { t } = useTranslation('sources')

  const reassurancePoints = [
    t(
      'dashboard.emptyState.points.detect',
      'We detect datasets, references, and layers automatically.'
    ),
    t(
      'dashboard.emptyState.points.review',
      'You can review the proposed configuration before import.'
    ),
    t(
      'dashboard.emptyState.points.update',
      'You can add or update files later from the same workspace.'
    ),
  ]

  return (
    <div className="flex h-full items-start justify-center overflow-auto p-6">
      <div className="w-full max-w-5xl space-y-6">
        <div className="space-y-2 text-center">
          <div className="inline-flex items-center gap-2 rounded-full border bg-background px-3 py-1 text-xs font-medium text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5" />
            {t('dashboard.emptyState.badge', 'Data workspace')}
          </div>
          <h1 className="text-3xl font-semibold tracking-tight">
            {t('dashboard.emptyState.title', 'Import your data')}
          </h1>
          <p className="mx-auto max-w-3xl text-sm leading-6 text-muted-foreground">
            {t(
              'dashboard.emptyState.description',
              'Start by adding your CSV, taxonomy, and spatial files. Niamoto will analyze them and help you configure the project.'
            )}
          </p>
        </div>

        <Card className="border-border/70">
          <CardHeader className="space-y-1 pb-4 text-center">
            <CardTitle className="text-lg">
              {t('dashboard.emptyState.dropzoneTitle', 'Drop files to begin')}
            </CardTitle>
            <CardDescription>
              {t(
                'dashboard.emptyState.dropzoneDescription',
                'CSV, GeoPackage, GeoJSON, TIFF, and related support files.'
              )}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <FileUploadZone onFilesReady={onFilesReady} />

            <div className="flex justify-center">
              <Button variant="outline" onClick={onOpenImportWorkspace}>
                <FolderUp className="mr-2 h-4 w-4" />
                {t(
                  'dashboard.emptyState.openWorkspace',
                  'Open import workspace'
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-3 md:grid-cols-3">
          {reassurancePoints.map((point) => (
            <Card key={point} className="border-border/60 bg-muted/20">
              <CardContent className="flex items-start gap-3 p-4">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                <p className="text-sm text-muted-foreground">{point}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
