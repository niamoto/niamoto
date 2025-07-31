import { useTranslation } from 'react-i18next';

export function ExportPage() {
  const { t } = useTranslation('export');

  return (
    <div className="p-6">
      <h2 className="mb-4 text-2xl font-bold">{t('title')}</h2>
      <p className="text-muted-foreground">
        {t('description')}
      </p>
    </div>
  )
}
