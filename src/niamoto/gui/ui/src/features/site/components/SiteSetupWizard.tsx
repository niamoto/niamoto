/**
 * SiteSetupWizard - First-launch setup wizard for the Site module
 *
 * 4 steps: Choose preset → Review structure → Customize theme → Preview
 * Shown when siteConfig has no static_pages and no navigation (empty site).
 * Replaces center panel content — not a modal.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ChevronRight,
  ChevronLeft,
  Check,
  SkipForward,
  Home,
  FileText,
  Users,
  Mail,
  BookOpen,
  Download,
  List,
  type LucideIcon,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import type { SiteSettings, GroupInfo, StaticPage, FooterSection } from '@/shared/hooks/useSiteConfig'
import type { UnifiedTreeItem } from '../hooks/useUnifiedSiteTree'
import { SITE_PRESETS, applySitePreset, type SitePreset } from '../data/sitePresets'
import { ThemeConfigForm } from './ThemeConfigForm'

// Template icon mapping for preset cards
const PRESET_TEMPLATE_ICONS: Record<string, LucideIcon> = {
  'index.html': Home,
  'page.html': FileText,
  'team.html': Users,
  'contact.html': Mail,
  'bibliography.html': BookOpen,
  'resources.html': Download,
  'glossary.html': List,
}

// =============================================================================
// STEP COMPONENTS
// =============================================================================

function StepPresetSelector({
  groups,
  onSelect,
}: {
  groups: GroupInfo[]
  onSelect: (preset: SitePreset) => void
}) {
  const { t } = useTranslation('site')

  return (
    <div className="flex flex-col items-center justify-center min-h-[350px]">
      <h2 className="text-xl font-semibold mb-2">{t('presets.title')}</h2>
      <p className="text-sm text-muted-foreground mb-6 text-center max-w-md">
        {t('presets.description')}
      </p>
      <div className="grid gap-4 sm:grid-cols-3 w-full max-w-2xl">
        {SITE_PRESETS.map(preset => (
          <button
            key={preset.id}
            className="p-5 rounded-lg border hover:border-primary/50 hover:bg-muted/30 transition-colors text-left group"
            onClick={() => onSelect(preset)}
          >
            <h3 className="font-medium mb-2">{t(preset.nameKey)}</h3>
            <p className="text-xs text-muted-foreground mb-3">{t(preset.descriptionKey)}</p>
            <div className="flex flex-wrap gap-1">
              {preset.pages.map(p => {
                const Icon = PRESET_TEMPLATE_ICONS[p.template] || FileText
                return (
                  <Badge key={p.name} variant="secondary" className="text-[10px] gap-1 font-normal">
                    <Icon className="h-3 w-3" />
                    {p.name}
                  </Badge>
                )
              })}
              {groups.length > 0 && (
                <Badge variant="outline" className="text-[10px] font-normal">
                  +{groups.length} collections
                </Badge>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

function StepReviewStructure({
  tree,
}: {
  tree: UnifiedTreeItem[]
}) {
  const { t } = useTranslation('site')
  const menuItems = tree.filter(i => i.visible)
  const hiddenItems = tree.filter(i => !i.visible)

  const getLabel = (item: UnifiedTreeItem) =>
    typeof item.label === 'string' ? item.label : Object.values(item.label)[0] as string || '—'

  return (
    <div className="max-w-lg mx-auto">
      <h3 className="font-medium mb-1">{t('wizard.step2')}</h3>
      <p className="text-sm text-muted-foreground mb-4">{t('wizard.step2Desc')}</p>
      <div className="space-y-1 border rounded-lg p-3">
        {menuItems.map(item => (
          <div key={item.id} className="flex items-center gap-2 px-2 py-1.5 text-sm">
            <div className="h-2 w-2 rounded-full bg-green-500" />
            <span>{getLabel(item)}</span>
            {item.template && (
              <Badge variant="outline" className="text-[9px] h-4 font-normal ml-auto">
                {item.template.replace('.html', '')}
              </Badge>
            )}
            {item.type === 'collection' && (
              <Badge variant="secondary" className="text-[9px] h-4 font-normal ml-auto">
                collection
              </Badge>
            )}
            {item.children.length > 0 && (
              <div className="ml-6 space-y-1">
                {item.children.map(child => (
                  <div key={child.id} className="flex items-center gap-2 px-2 py-1 text-sm text-muted-foreground">
                    <div className="h-1.5 w-1.5 rounded-full bg-green-400" />
                    <span>{getLabel(child)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {hiddenItems.length > 0 && (
          <>
            <div className="border-t my-2" />
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider px-2">
              {t('unifiedTree.notInMenu')}
            </p>
            {hiddenItems.map(item => (
              <div key={item.id} className="flex items-center gap-2 px-2 py-1 text-sm text-muted-foreground">
                <div className="h-2 w-2 rounded-full bg-muted-foreground/30" />
                <span>{getLabel(item)}</span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  )
}

function StepTheme({
  site,
  onChange,
}: {
  site: SiteSettings
  onChange: (site: SiteSettings) => void
}) {
  const { t } = useTranslation('site')
  return (
    <div className="max-w-2xl mx-auto">
      <h3 className="font-medium mb-1">{t('wizard.step3')}</h3>
      <p className="text-sm text-muted-foreground mb-4">{t('wizard.step3Desc')}</p>
      <ThemeConfigForm config={site} onChange={onChange} />
    </div>
  )
}

function StepPreview({
  tree,
  pages,
}: {
  tree: UnifiedTreeItem[]
  pages: StaticPage[]
}) {
  const { t } = useTranslation('site')
  const menuCount = tree.filter(i => i.visible).length

  return (
    <div className="flex flex-col items-center justify-center min-h-[300px]">
      <div className="text-center mb-6">
        <div className="inline-flex items-center justify-center h-16 w-16 rounded-full bg-green-100 mb-4">
          <Check className="h-8 w-8 text-green-600" />
        </div>
        <h3 className="font-medium text-lg">{t('wizard.step4')}</h3>
        <p className="text-sm text-muted-foreground mt-1">{t('wizard.step4Desc')}</p>
      </div>
      <div className="grid grid-cols-3 gap-6 text-center">
        <div>
          <p className="text-2xl font-semibold">{pages.length}</p>
          <p className="text-xs text-muted-foreground">pages</p>
        </div>
        <div>
          <p className="text-2xl font-semibold">{menuCount}</p>
          <p className="text-xs text-muted-foreground">menu items</p>
        </div>
        <div>
          <p className="text-2xl font-semibold">{tree.filter(i => i.type === 'collection').length}</p>
          <p className="text-xs text-muted-foreground">collections</p>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// MAIN WIZARD
// =============================================================================

interface SiteSetupWizardProps {
  groups: GroupInfo[]
  editedSite: SiteSettings
  onComplete: (result: {
    tree: UnifiedTreeItem[]
    pages: StaticPage[]
    footerSections: FooterSection[]
    site: SiteSettings
  }) => void
  onSetEditedSite: (site: SiteSettings) => void
}

export function SiteSetupWizard({
  groups,
  editedSite,
  onComplete,
  onSetEditedSite,
}: SiteSetupWizardProps) {
  const { t } = useTranslation('site')
  const [step, setStep] = useState(0)
  const [presetResult, setPresetResult] = useState<{
    tree: UnifiedTreeItem[]
    pages: StaticPage[]
    footerSections: FooterSection[]
  } | null>(null)

  const STEPS = [
    { label: t('wizard.step1') },
    { label: t('wizard.step2') },
    { label: t('wizard.step3') },
    { label: t('wizard.step4') },
  ]

  const handleSelectPreset = (preset: SitePreset) => {
    const result = applySitePreset(preset, groups)
    setPresetResult({
      tree: result.tree,
      pages: result.staticPages,
      footerSections: result.footerSections,
    })
    setStep(1)
  }

  const handleSkipAll = () => {
    // Apply minimal preset and finish
    const minimal = SITE_PRESETS[0]
    const result = applySitePreset(minimal, groups)
    onComplete({
      tree: result.tree,
      pages: result.staticPages,
      footerSections: result.footerSections,
      site: editedSite,
    })
  }

  const handleFinish = () => {
    if (!presetResult) return
    onComplete({
      tree: presetResult.tree,
      pages: presetResult.pages,
      footerSections: presetResult.footerSections,
      site: editedSite,
    })
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-6">
        {/* Header with progress */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-lg font-semibold">{t('wizard.title')}</h1>
            <p className="text-xs text-muted-foreground">
              {t('wizard.stepOf', { current: step + 1, total: STEPS.length })}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={handleSkipAll} className="text-muted-foreground">
            <SkipForward className="h-4 w-4 mr-1" />
            {t('wizard.skipAll')}
          </Button>
        </div>

        {/* Step indicators */}
        <div className="flex items-center gap-2 mb-8">
          {STEPS.map((s, i) => (
            <div key={i} className="flex items-center gap-2 flex-1">
              <div className={cn(
                'flex items-center justify-center h-7 w-7 rounded-full text-xs font-medium transition-colors',
                i < step ? 'bg-primary text-primary-foreground' :
                i === step ? 'bg-primary/20 text-primary border border-primary' :
                'bg-muted text-muted-foreground'
              )}>
                {i < step ? <Check className="h-3.5 w-3.5" /> : i + 1}
              </div>
              <span className={cn(
                'text-xs hidden sm:block',
                i === step ? 'text-foreground font-medium' : 'text-muted-foreground'
              )}>
                {s.label}
              </span>
              {i < STEPS.length - 1 && (
                <div className={cn(
                  'flex-1 h-px',
                  i < step ? 'bg-primary' : 'bg-border'
                )} />
              )}
            </div>
          ))}
        </div>

        {/* Step content */}
        <div className="min-h-[350px]">
          {step === 0 && (
            <StepPresetSelector groups={groups} onSelect={handleSelectPreset} />
          )}
          {step === 1 && presetResult && (
            <StepReviewStructure tree={presetResult.tree} />
          )}
          {step === 2 && (
            <StepTheme site={editedSite} onChange={onSetEditedSite} />
          )}
          {step === 3 && presetResult && (
            <StepPreview tree={presetResult.tree} pages={presetResult.pages} />
          )}
        </div>

        {/* Navigation buttons */}
        {step > 0 && (
          <div className="flex items-center justify-between mt-6 pt-4 border-t">
            <Button variant="outline" size="sm" onClick={() => setStep(s => s - 1)}>
              <ChevronLeft className="h-4 w-4 mr-1" />
              {t('wizard.back')}
            </Button>
            <div className="flex items-center gap-2">
              {step < STEPS.length - 1 && (
                <Button variant="ghost" size="sm" onClick={() => setStep(s => s + 1)}>
                  {t('wizard.skip')}
                </Button>
              )}
              {step < STEPS.length - 1 ? (
                <Button size="sm" onClick={() => setStep(s => s + 1)}>
                  {t('wizard.next')}
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              ) : (
                <Button size="sm" onClick={handleFinish}>
                  <Check className="h-4 w-4 mr-1" />
                  {t('wizard.finish')}
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </ScrollArea>
  )
}
