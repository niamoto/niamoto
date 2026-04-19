import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'

import { createDesktopCommandRouter } from '../shell/commands.mjs'

async function createTempFixture() {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'niamoto-electron-'))
  return {
    root,
    sharedDesktopConfigPath: path.join(root, 'shared', 'desktop-config.json'),
    electronSettingsPath: path.join(root, 'electron', 'settings.json'),
    electronLogDir: path.join(root, 'electron', 'logs'),
  }
}

async function createValidProject(root, name = 'demo-project') {
  const projectPath = path.join(root, name)
  await fs.mkdir(path.join(projectPath, 'db'), { recursive: true })
  await fs.mkdir(path.join(projectPath, 'config'), { recursive: true })
  await fs.writeFile(path.join(projectPath, 'config', 'config.yml'), 'project: {}\n')
  return projectPath
}

test('desktop command router keeps project selection in the shared config', async () => {
  const paths = await createTempFixture()
  const projectPath = await createValidProject(paths.root)

  const router = createDesktopCommandRouter({
    paths,
    shellApi: {
      pickDirectory: async () => null,
      openExternalUrl: async () => {},
      openDevTools: () => {},
    },
    isDev: false,
  })

  await router('set_current_project', { path: projectPath })

  assert.equal(await router('get_current_project'), projectPath)
  const recentProjects = await router('get_recent_projects')
  assert.equal(recentProjects.length, 1)
  assert.equal(recentProjects[0].path, projectPath)
  assert.equal(recentProjects[0].name, path.basename(projectPath))
  assert.match(recentProjects[0].last_accessed, /\d{4}-\d{2}-\d{2}T/)
})

test('desktop command router stores settings separately from shared project config', async () => {
  const paths = await createTempFixture()
  const router = createDesktopCommandRouter({
    paths,
    shellApi: {
      pickDirectory: async () => null,
      openExternalUrl: async () => {},
      openDevTools: () => {},
    },
    isDev: false,
  })

  await router('set_app_settings', {
    settings: {
      auto_load_last_project: false,
      ui_language: 'fr',
      debug_mode: true,
    },
  })

  assert.deepEqual(await router('get_app_settings'), {
    auto_load_last_project: false,
    ui_language: 'fr',
    debug_mode: true,
  })

  await assert.rejects(fs.access(paths.sharedDesktopConfigPath))
})

test('desktop command router routes external URLs and guards devtools', async () => {
  const paths = await createTempFixture()
  const openedUrls = []
  let devtoolsOpened = false

  const router = createDesktopCommandRouter({
    paths,
    shellApi: {
      pickDirectory: async () => null,
      openExternalUrl: async (url) => {
        openedUrls.push(url)
      },
      openDevTools: () => {
        devtoolsOpened = true
      },
    },
    isDev: false,
  })

  await router('open_external_url', { url: 'https://niamoto.io' })
  assert.deepEqual(openedUrls, ['https://niamoto.io/'])

  await assert.rejects(
    router('open_desktop_devtools'),
    /Desktop debug mode is disabled/
  )

  await router('set_app_settings', {
    settings: {
      debug_mode: true,
    },
  })
  await router('open_desktop_devtools')
  assert.equal(devtoolsOpened, true)
})
