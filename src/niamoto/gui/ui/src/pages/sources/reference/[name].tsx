/**
 * Reference Detail Page
 * Route: /sources/reference/:name
 */

import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useReferences } from '@/hooks/useReferences'
import { ReferenceDetailPanel } from '@/components/panels/ReferenceDetailPanel'

export default function ReferencePage() {
  const { t } = useTranslation(['sources', 'common'])
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const { data: referencesData, isLoading } = useReferences()
  const references = referencesData?.references ?? []

  const reference = references.find((r) => r.name === name)

  // Show loading state while fetching
  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-pulse text-muted-foreground">{t('common:status.loading')}</div>
      </div>
    )
  }

  if (!reference) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-lg font-medium">{t('reference.notFound')}</h2>
          <p className="text-muted-foreground mt-1">
            {t('reference.notFoundDesc', { name })}
          </p>
          <button
            className="mt-4 text-primary hover:underline"
            onClick={() => navigate('/sources')}
          >
            {t('reference.backToDashboard')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto">
      <ReferenceDetailPanel
        referenceName={reference.name}
        tableName={reference.table_name}
        kind={reference.kind}
        entityCount={reference.entity_count}
        onBack={() => navigate('/sources')}
      />
    </div>
  )
}
