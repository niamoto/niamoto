/**
 * Dataset Detail Page
 * Route: /sources/dataset/:name
 */

import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useDatasets } from '@/hooks/useDatasets'
import { DatasetDetailPanel } from '@/components/panels/DatasetDetailPanel'

export default function DatasetPage() {
  const { t } = useTranslation(['sources', 'common'])
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const { data: datasetsData, isLoading } = useDatasets()
  const datasets = datasetsData?.datasets ?? []

  const dataset = datasets.find((d) => d.name === name)

  // Show loading state while fetching
  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-pulse text-muted-foreground">{t('common:status.loading')}</div>
      </div>
    )
  }

  if (!dataset) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-lg font-medium">{t('dataset.notFound')}</h2>
          <p className="text-muted-foreground mt-1">
            {t('dataset.notFoundDesc', { name })}
          </p>
          <button
            className="mt-4 text-primary hover:underline"
            onClick={() => navigate('/sources')}
          >
            {t('dataset.backToDashboard')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto">
      <DatasetDetailPanel
        datasetName={dataset.name}
        tableName={dataset.table_name}
        entityCount={dataset.entity_count}
        onBack={() => navigate('/sources')}
      />
    </div>
  )
}
