/**
 * SiteBuilderPreview - Preview components for the Site Builder
 *
 * Contains SitePreview (static page preview) and GroupIndexPreviewPanel
 * (collection index preview), extracted from SiteBuilder.tsx.
 */

import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { PreviewFrame, type DeviceSize } from '@/components/ui/preview-frame'
import {
  type SiteSettings,
  type NavigationItem,
  type FooterSection,
  type StaticPage,
} from '@/shared/hooks/useSiteConfig'
import { previewTemplate } from '@/shared/hooks/site-config/siteConfigApi'

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
  const previewRequest = useMemo(() => {
    if (!page) {
      return null
    }

    const context: Record<string, unknown> = { ...page.context }

    if (fileContent && page.context?.content_source) {
      context.content_markdown = fileContent
      delete context.content_source
    }

    if (page.context?.title) {
      context.title = page.context.title
    }

    return {
      template: page.template || 'page.html',
      context,
      site: site as Record<string, unknown>,
      navigation: navigation.map((item) => ({
        text: item.text,
        url: item.url,
        children: item.children,
      })),
      footer_navigation: footerNavigation.map((section) => ({
        title: section.title,
        links: section.links,
      })),
      output_file: page.output_file,
      gui_lang: i18n.language?.split('-')[0] || 'fr',
    }
  }, [fileContent, footerNavigation, i18n.language, navigation, page, site])

  const {
    data: previewData,
    error: previewError,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ['site-template-preview', previewRequest],
    queryFn: () => previewTemplate(previewRequest!),
    enabled: Boolean(previewRequest),
  })

  const html = previewRequest
    ? (previewData?.html ?? (
        previewError instanceof Error
          ? `<div class="text-red-500 p-4">Erreur: ${previewError.message}</div>`
          : ''
      ))
    : ''

  return (
    <PreviewFrame
      html={html}
      isLoading={isFetching}
      device={device}
      onDeviceChange={onDeviceChange}
      onRefresh={() => {
        if (previewRequest) {
          void refetch()
        }
      }}
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
