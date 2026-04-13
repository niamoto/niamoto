/**
 * Types partagés pour le système de preview widgets.
 *
 * SYNC : le contrat Python correspondant est dans
 * src/niamoto/gui/api/services/preview_engine/models.py
 */

export type PreviewMode = 'thumbnail' | 'full'

/** Configuration plugin validée côté serveur */
type PluginParams = Record<string, unknown>

export interface InlinePreviewConfig {
  transformer_plugin: string
  transformer_params: PluginParams
  widget_plugin: string
  widget_params?: PluginParams | null
  widget_title?: string
}

/**
 * Descripteur de preview — identifie un widget à prévisualiser.
 *
 * Deux modes :
 * - Par template_id : résolution via transform.yml / export.yml
 * - Par inline : configuration directe transformer + widget
 */
export interface PreviewDescriptor {
  templateId?: string
  groupBy?: string
  source?: string
  entityId?: string
  mode: PreviewMode
  inline?: InlinePreviewConfig
}

/** État du rendu preview (retourné par usePreviewFrame) */
export interface PreviewState {
  html: string | null
  loading: boolean
  error: string | null
  timingMs: number | null
}
