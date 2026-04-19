import fs from 'node:fs/promises'
import path from 'node:path'

const WINDOWS_RESERVED_PROJECT_NAMES = new Set([
  'CON',
  'PRN',
  'AUX',
  'NUL',
  'COM1',
  'COM2',
  'COM3',
  'COM4',
  'COM5',
  'COM6',
  'COM7',
  'COM8',
  'COM9',
  'LPT1',
  'LPT2',
  'LPT3',
  'LPT4',
  'LPT5',
  'LPT6',
  'LPT7',
  'LPT8',
  'LPT9',
])

const DEFAULT_SETTINGS = {
  auto_load_last_project: true,
  ui_language: 'auto',
  debug_mode: false,
}

function isRecord(value) {
  return typeof value === 'object' && value !== null
}

function nowIso() {
  return new Date().toISOString()
}

async function ensureParentDir(filePath) {
  await fs.mkdir(path.dirname(filePath), { recursive: true })
}

async function readJsonFile(filePath, fallbackValue) {
  try {
    const raw = await fs.readFile(filePath, 'utf8')
    return JSON.parse(raw)
  } catch (error) {
    if (error && typeof error === 'object' && error.code === 'ENOENT') {
      return fallbackValue
    }
    throw error
  }
}

async function writeJsonFile(filePath, value) {
  await ensureParentDir(filePath)
  await fs.writeFile(filePath, JSON.stringify(value, null, 2), 'utf8')
}

function normalizeUiLanguage(value) {
  return value === 'fr' || value === 'en' || value === 'auto' ? value : 'auto'
}

function normalizeSettings(value) {
  if (!isRecord(value)) {
    return { ...DEFAULT_SETTINGS }
  }

  return {
    auto_load_last_project:
      typeof value.auto_load_last_project === 'boolean'
        ? value.auto_load_last_project
        : DEFAULT_SETTINGS.auto_load_last_project,
    ui_language: normalizeUiLanguage(value.ui_language),
    debug_mode:
      typeof value.debug_mode === 'boolean'
        ? value.debug_mode
        : DEFAULT_SETTINGS.debug_mode,
  }
}

function normalizeRecentProjects(value) {
  if (!Array.isArray(value)) {
    return []
  }

  return value.filter((entry) => {
    return (
      isRecord(entry) &&
      typeof entry.path === 'string' &&
      typeof entry.name === 'string' &&
      typeof entry.last_accessed === 'string'
    )
  })
}

async function readSharedDesktopConfig(sharedConfigPath) {
  const raw = await readJsonFile(sharedConfigPath, {})

  return {
    raw: isRecord(raw) ? raw : {},
    current_project: typeof raw.current_project === 'string' ? raw.current_project : null,
    recent_projects: normalizeRecentProjects(raw.recent_projects),
    last_updated: typeof raw.last_updated === 'string' ? raw.last_updated : nowIso(),
  }
}

async function writeSharedDesktopConfig(sharedConfigPath, nextConfig) {
  const existingConfig = await readSharedDesktopConfig(sharedConfigPath)
  const raw = {
    ...existingConfig.raw,
    current_project: nextConfig.current_project,
    recent_projects: nextConfig.recent_projects,
    last_updated: nextConfig.last_updated,
  }

  await writeJsonFile(sharedConfigPath, raw)
}

async function readSettings(settingsPath) {
  const raw = await readJsonFile(settingsPath, DEFAULT_SETTINGS)
  return normalizeSettings(raw)
}

async function writeSettings(settingsPath, settings) {
  await writeJsonFile(settingsPath, normalizeSettings(settings))
}

async function pathExists(targetPath) {
  try {
    await fs.access(targetPath)
    return true
  } catch {
    return false
  }
}

export async function validateProjectPath(projectPath) {
  const stat = await fs
    .stat(projectPath)
    .catch(() => null)

  if (!stat) {
    throw new Error(`Path does not exist: ${projectPath}`)
  }

  if (!stat.isDirectory()) {
    throw new Error(`Path is not a directory: ${projectPath}`)
  }

  const requiredPaths = [
    path.join(projectPath, 'db'),
    path.join(projectPath, 'config'),
    path.join(projectPath, 'config', 'config.yml'),
  ]

  const [dbExists, configDirExists, configFileExists] = await Promise.all(
    requiredPaths.map((requiredPath) => pathExists(requiredPath))
  )

  if (!dbExists) {
    throw new Error(`Not a valid Niamoto project: missing 'db' directory in ${projectPath}`)
  }

  if (!configDirExists) {
    throw new Error(
      `Not a valid Niamoto project: missing 'config' directory in ${projectPath}`
    )
  }

  if (!configFileExists) {
    throw new Error(
      `Not a valid Niamoto project: missing 'config/config.yml' in ${projectPath}`
    )
  }

  return true
}

export function validateProjectName(name) {
  const trimmed = name.trim()

  if (!trimmed) {
    throw new Error('Project name cannot be empty')
  }

  if (trimmed !== name) {
    throw new Error('Project name cannot start or end with whitespace')
  }

  if (trimmed === '.' || trimmed === '..') {
    throw new Error('Project name is invalid')
  }

  if (trimmed.endsWith('.') || trimmed.endsWith(' ')) {
    throw new Error('Project name cannot end with a dot or space')
  }

  if (/[\u0000-\u001f<>:"/\\|?*]/.test(trimmed)) {
    throw new Error('Project name contains unsupported characters (< > : " / \\ | ? *)')
  }

  const windowsStem = trimmed.split('.')[0].toUpperCase()
  if (WINDOWS_RESERVED_PROJECT_NAMES.has(windowsStem)) {
    throw new Error(`Project name '${trimmed}' is reserved on Windows and cannot be used`)
  }

  return trimmed
}

export async function createProjectScaffold(projectPath, name) {
  await fs.mkdir(projectPath, { recursive: true })

  for (const subdir of [
    'db',
    'config',
    'imports',
    'logs',
    path.join('exports', 'web'),
    path.join('exports', 'api'),
  ]) {
    await fs.mkdir(path.join(projectPath, subdir), { recursive: true })
  }

  const configContent = `# Niamoto Project Configuration
project:
  name: "${name}"
  created_at: "${nowIso()}"

database:
  path: db/niamoto.duckdb

logs:
  path: logs

exports:
  web: exports/web
  api: exports/api
`

  await fs.writeFile(path.join(projectPath, 'config', 'config.yml'), configContent, 'utf8')

  for (const configFile of ['import.yml', 'transform.yml', 'export.yml']) {
    await fs.writeFile(
      path.join(projectPath, 'config', configFile),
      `# ${configFile.replace('.yml', '')} configuration\n`,
      'utf8'
    )
  }
}

function requireStringArg(args, key) {
  const value = args?.[key]
  if (typeof value !== 'string') {
    throw new Error(`Missing required argument: ${key}`)
  }
  return value
}

export function createDesktopCommandRouter(options) {
  const { paths, shellApi, isDev } = options

  return async function invoke(command, args = {}) {
    if (command === 'get_current_project') {
      const config = await readSharedDesktopConfig(paths.sharedDesktopConfigPath)
      return config.current_project
    }

    if (command === 'get_recent_projects') {
      const config = await readSharedDesktopConfig(paths.sharedDesktopConfigPath)
      return config.recent_projects
    }

    if (command === 'validate_recent_projects') {
      const config = await readSharedDesktopConfig(paths.sharedDesktopConfigPath)
      return Promise.all(
        config.recent_projects.map(async (project) => {
          try {
            await validateProjectPath(project.path)
            return { path: project.path, valid: true }
          } catch {
            return { path: project.path, valid: false }
          }
        })
      )
    }

    if (command === 'validate_project') {
      await validateProjectPath(requireStringArg(args, 'path'))
      return true
    }

    if (command === 'set_current_project') {
      const projectPath = requireStringArg(args, 'path')
      await validateProjectPath(projectPath)

      const config = await readSharedDesktopConfig(paths.sharedDesktopConfigPath)
      const projectEntry = {
        path: projectPath,
        name: path.basename(projectPath),
        last_accessed: nowIso(),
      }

      const recentProjects = [
        projectEntry,
        ...config.recent_projects.filter((project) => project.path !== projectPath),
      ].slice(0, 10)

      await writeSharedDesktopConfig(paths.sharedDesktopConfigPath, {
        current_project: projectPath,
        recent_projects: recentProjects,
        last_updated: projectEntry.last_accessed,
      })
      return null
    }

    if (command === 'remove_recent_project') {
      const projectPath = requireStringArg(args, 'path')
      const config = await readSharedDesktopConfig(paths.sharedDesktopConfigPath)
      const recentProjects = config.recent_projects.filter(
        (project) => project.path !== projectPath
      )
      await writeSharedDesktopConfig(paths.sharedDesktopConfigPath, {
        current_project:
          config.current_project === projectPath ? null : config.current_project,
        recent_projects: recentProjects,
        last_updated: nowIso(),
      })
      return null
    }

    if (command === 'browse_project_folder') {
      const selectedPath = await shellApi.pickDirectory({
        title: 'Select Niamoto Project Folder',
      })
      if (!selectedPath) {
        return null
      }

      await validateProjectPath(selectedPath)
      return selectedPath
    }

    if (command === 'browse_folder') {
      return shellApi.pickDirectory({
        title: 'Select Location',
      })
    }

    if (command === 'create_project') {
      const projectName = validateProjectName(requireStringArg(args, 'name'))
      const location = requireStringArg(args, 'location')
      const projectPath = path.join(location, projectName)

      if (await pathExists(projectPath)) {
        throw new Error(`Directory already exists: ${projectPath}`)
      }

      if (!(await pathExists(location))) {
        throw new Error(`Parent directory does not exist: ${location}`)
      }

      await createProjectScaffold(projectPath, projectName)
      await invoke('set_current_project', { path: projectPath })
      return projectPath
    }

    if (command === 'get_app_settings') {
      return readSettings(paths.electronSettingsPath)
    }

    if (command === 'set_app_settings') {
      await writeSettings(paths.electronSettingsPath, args?.settings ?? {})
      return null
    }

    if (command === 'open_external_url') {
      const url = requireStringArg(args, 'url').trim()
      const parsedUrl = new URL(url)

      if (!['http:', 'https:', 'mailto:'].includes(parsedUrl.protocol)) {
        throw new Error(
          `Unsupported URL scheme: ${parsedUrl.protocol.replace(':', '')}. Only http, https, and mailto are allowed.`
        )
      }

      await shellApi.openExternalUrl(parsedUrl.toString())
      return null
    }

    if (command === 'open_desktop_devtools') {
      const settings = await readSettings(paths.electronSettingsPath)
      if (!isDev && !settings.debug_mode) {
        throw new Error('Desktop debug mode is disabled')
      }

      shellApi.openDevTools()
      return null
    }

    throw new Error(`Unsupported desktop command: ${command}`)
  }
}
