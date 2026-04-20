export interface BuildGate {
  canGenerate: boolean
  showConfigurationRequired: boolean
  siteBuilderPath: string | null
}

const SITE_BUILDER_PATH = '/site/pages'

export function getBuildGate(siteStatus: string | null | undefined): BuildGate {
  const showConfigurationRequired =
    siteStatus === 'unconfigured' || siteStatus === 'never_run'
  const isResolved = siteStatus !== null && siteStatus !== undefined

  return {
    canGenerate: isResolved && !showConfigurationRequired,
    showConfigurationRequired,
    siteBuilderPath: showConfigurationRequired ? SITE_BUILDER_PATH : null,
  }
}
