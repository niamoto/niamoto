import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { AlertCircle, CheckCircle, Database, FolderOpen, FileText } from 'lucide-react'
import { getDiagnosticInfo } from '@/shared/lib/api/diagnostics'
import { sharedQueryKeys } from '@/shared/lib/api/queryKeys'

export function DiagnosticPanel() {
  const { t } = useTranslation('common')
  const {
    data: diagnostic,
    isLoading: loading,
    error,
  } = useQuery({
    queryKey: sharedQueryKeys.diagnostic(),
    queryFn: getDiagnosticInfo,
    staleTime: 30_000,
  })

  if (loading) {
    return (
      <div className="rounded-lg border bg-card p-4">
        <p className="text-sm text-muted-foreground">{t('diagnostic.loadingDiagnostic')}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-destructive" />
          <p className="text-sm font-medium">{t('diagnostic.diagnosticError')}</p>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">{error.message}</p>
      </div>
    )
  }

  if (!diagnostic) {
    return null
  }

  return (
    <div className="space-y-4">
      {/* Working Directory */}
      <div className="rounded-lg border bg-card p-4">
        <div className="flex items-center gap-2 mb-2">
          <FolderOpen className="h-5 w-5 text-primary" />
          <h3 className="font-medium">{t('diagnostic.workingDirectory')}</h3>
        </div>
        <p className="text-sm text-muted-foreground font-mono">{diagnostic.working_directory}</p>
      </div>

      {/* Database */}
      <div className="rounded-lg border bg-card p-4">
        <div className="flex items-center gap-2 mb-2">
          <Database className="h-5 w-5 text-primary" />
          <h3 className="font-medium">{t('diagnostic.database')}</h3>
          {diagnostic.database.exists ? (
            <CheckCircle className="h-4 w-4 text-green-500 ml-auto" />
          ) : (
            <AlertCircle className="h-4 w-4 text-destructive ml-auto" />
          )}
        </div>
        <p className="text-sm text-muted-foreground font-mono mb-2">
          {diagnostic.database.path || t('diagnostic.notFound')}
        </p>
        {diagnostic.database.exists && diagnostic.database.tables.length > 0 && (
          <div className="mt-2">
            <p className="text-xs text-muted-foreground mb-1">
              {t('diagnostic.tables')} ({diagnostic.database.tables.length}) :
            </p>
            <div className="flex flex-wrap gap-1">
              {diagnostic.database.tables.slice(0, 10).map((table) => (
                <span
                  key={table}
                  className="inline-flex items-center rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary"
                >
                  {table}
                </span>
              ))}
              {diagnostic.database.tables.length > 10 && (
                <span className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs font-medium">
                  {t('diagnostic.moreOthers', { count: diagnostic.database.tables.length - 10 })}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Config Files */}
      <div className="rounded-lg border bg-card p-4">
        <div className="flex items-center gap-2 mb-2">
          <FileText className="h-5 w-5 text-primary" />
          <h3 className="font-medium">{t('diagnostic.configFiles')}</h3>
        </div>
        <div className="space-y-2">
          {Object.entries(diagnostic.config_files).map(([filename, info]) => (
            <div key={filename} className="flex items-center justify-between">
              <span className="text-sm font-mono">{filename}</span>
              {info.exists ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : (
                <AlertCircle className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
