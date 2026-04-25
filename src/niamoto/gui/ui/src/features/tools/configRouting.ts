import type { ConfigType } from './hooks/useConfig'

export const CONFIG_TAB_VALUES = ['config', 'import', 'transform', 'export'] as const satisfies readonly ConfigType[]

export function normalizeConfigTab(value: string | null | undefined): ConfigType | null {
  if (!value) {
    return null
  }

  return CONFIG_TAB_VALUES.includes(value as ConfigType) ? (value as ConfigType) : null
}

export function buildConfigEditorPath(configName: ConfigType): string {
  if (configName === 'config') {
    return '/tools/config-editor'
  }

  return `/tools/config-editor?config=${configName}`
}
