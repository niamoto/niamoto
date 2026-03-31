/**
 * SiteBuilderPreview - Preview components for the Site Builder
 *
 * Contains SitePreview (static page preview) and GroupIndexPreviewPanel
 * (collection index preview), extracted from SiteBuilder.tsx.
 */

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { PreviewFrame, type DeviceSize } from '@/components/ui/preview-frame'
import {
  useTemplatePreview,
  type SiteSettings,
  type NavigationItem,
  type FooterSection,
  type StaticPage,
} from '@/shared/hooks/useSiteConfig'

// =============================================================================
// SITE PREVIEW (static page template preview)
// =============================================================================

export interface SitePreviewProps {
  page: StaticPage | null
  site: SiteSettings
  navigation: NavigationItem[]
  footerNavigation: FooterSection[]
  device: DeviceSize
  onDeviceChange: (device: DeviceSize) => void
  fileContent?: string
  onLinkClick?: (href: string) => void
  onClose?: () => void
}

export function SitePreview({ page, site, navigation, footerNavigation, device, onDeviceChange, fileContent, onLinkClick, onClose }: SitePreviewProps) {
  const { t, i18n } = useTranslation(['site', 'common'])
  const previewMutation = useTemplatePreview()
  const [html, setHtml] = useState('')

  const loadPreview = () => {
    if (page) {
      const context: Record<string, unknown> = { ...page.context }

      if (fileContent && page.context?.content_source) {
        context.content_markdown = fileContent
        delete context.content_source
      }

      if (page.context?.title) {
        context.title = page.context.title
      }

      previewMutation.mutate({
        template: page.template || 'page.html',
        context,
        site: site as Record<string, unknown>,
        navigation: navigation.map(n => ({
          text: n.text,
          url: n.url,
          children: n.children,
        })),
        footer_navigation: footerNavigation.map(s => ({
          title: s.title,
          links: s.links,
        })),
        output_file: page.output_file,
        gui_lang: i18n.language?.split('-')[0] || 'fr',
      }, {
        onSuccess: (data) => setHtml(data.html),
        onError: (error) => {
          setHtml(`<div class="text-red-500 p-4">Erreur: ${error.message}</div>`)
        },
      })
    } else {
      setHtml('')
    }
  }

  useEffect(() => {
    loadPreview()
  }, [page, site, navigation, footerNavigation, fileContent])

  return (
    <PreviewFrame
      html={html}
      isLoading={previewMutation.isPending}
      device={device}
      onDeviceChange={onDeviceChange}
      onRefresh={loadPreview}
      onClose={onClose}
      onLinkClick={onLinkClick}
      title={t('preview.title')}
      emptyMessage={t('preview.selectPageForPreview')}
    />
  )
}

// =============================================================================
// GROUP INDEX PREVIEW PANEL
// =============================================================================

export interface GroupIndexPreviewPanelProps {
  html: string | null
  isLoading: boolean
  device: DeviceSize
  onDeviceChange: (device: DeviceSize) => void
  groupName: string
  onLinkClick?: (href: string) => void
  onRefresh?: () => void
}

export function GroupIndexPreviewPanel({
  html,
  isLoading,
  device,
  onDeviceChange,
  groupName,
  onLinkClick,
  onRefresh,
}: GroupIndexPreviewPanelProps) {
  const { t } = useTranslation(['site', 'common'])

  return (
    <PreviewFrame
      html={html}
      isLoading={isLoading}
      device={device}
      onDeviceChange={onDeviceChange}
      onRefresh={onRefresh}
      onLinkClick={onLinkClick}
      title={`${t('preview.previewIndex')} - ${groupName}`}
    />
  )
}
