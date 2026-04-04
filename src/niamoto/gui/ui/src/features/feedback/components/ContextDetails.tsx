import { useTranslation } from 'react-i18next'
import type { FeedbackContext } from '../types'

interface ContextDetailsProps {
  context: FeedbackContext | null
}

export function ContextDetails({ context }: ContextDetailsProps) {
  const { t } = useTranslation('feedback')

  if (!context) return null

  return (
    <details className="text-xs text-muted-foreground">
      <summary className="cursor-pointer select-none py-1 hover:text-foreground transition-theme-fast">
        {t('context_label')}
      </summary>
      <div className="mt-2 rounded-theme-sm bg-muted/50 p-3 font-mono text-[11px] leading-relaxed">
        <table className="w-full">
          <tbody>
            <tr><td className="pr-3 text-muted-foreground/70">Version</td><td>{context.app_version}</td></tr>
            <tr><td className="pr-3 text-muted-foreground/70">OS</td><td className="break-all">{context.os}</td></tr>
            <tr><td className="pr-3 text-muted-foreground/70">Page</td><td>{context.current_page}</td></tr>
            <tr><td className="pr-3 text-muted-foreground/70">Mode</td><td>{context.runtime_mode}</td></tr>
            <tr><td className="pr-3 text-muted-foreground/70">{t('context_theme')}</td><td>{context.theme}</td></tr>
            <tr><td className="pr-3 text-muted-foreground/70">{t('context_language')}</td><td>{context.language}</td></tr>
            <tr><td className="pr-3 text-muted-foreground/70">{t('context_window')}</td><td>{context.window_size}</td></tr>
            {context.recent_errors && context.recent_errors.length > 0 && (
              <tr>
                <td className="pr-3 align-top text-muted-foreground/70">{t('context_errors')}</td>
                <td>{context.recent_errors.length} {t('context_recent')}</td>
              </tr>
            )}
            {context.diagnostic && (
              <tr>
                <td className="pr-3 align-top text-muted-foreground/70">{t('context_diagnostic')}</td>
                <td>{t('context_included')}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </details>
  )
}
