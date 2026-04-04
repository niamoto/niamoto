import { useTranslation } from 'react-i18next'
import { redactObject } from '../lib/redact'
import type { FeedbackContext } from '../types'

interface ContextDetailsProps {
  context: FeedbackContext | null
}

export function ContextDetails({ context }: ContextDetailsProps) {
  const { t } = useTranslation('feedback')

  if (!context) return null

  const redacted = redactObject(context)

  return (
    <details className="text-xs text-muted-foreground">
      <summary className="cursor-pointer select-none py-1 hover:text-foreground transition-colors">
        {t('context_label')}
      </summary>
      <div className="mt-2 rounded-theme-sm bg-muted/50 p-3 font-mono text-[11px] leading-relaxed">
        <table className="w-full">
          <tbody>
            <tr><td className="pr-3 text-muted-foreground/70">Version</td><td>{redacted.app_version}</td></tr>
            <tr><td className="pr-3 text-muted-foreground/70">OS</td><td className="break-all">{redacted.os}</td></tr>
            <tr><td className="pr-3 text-muted-foreground/70">Page</td><td>{redacted.current_page}</td></tr>
            <tr><td className="pr-3 text-muted-foreground/70">Mode</td><td>{redacted.runtime_mode}</td></tr>
            <tr><td className="pr-3 text-muted-foreground/70">Thème</td><td>{redacted.theme}</td></tr>
            <tr><td className="pr-3 text-muted-foreground/70">Langue</td><td>{redacted.language}</td></tr>
            <tr><td className="pr-3 text-muted-foreground/70">Fenêtre</td><td>{redacted.window_size}</td></tr>
            {redacted.recent_errors && redacted.recent_errors.length > 0 && (
              <tr>
                <td className="pr-3 align-top text-muted-foreground/70">Erreurs</td>
                <td>{redacted.recent_errors.length} récente(s)</td>
              </tr>
            )}
            {redacted.diagnostic && (
              <tr>
                <td className="pr-3 align-top text-muted-foreground/70">Diagnostic</td>
                <td>inclus</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </details>
  )
}
