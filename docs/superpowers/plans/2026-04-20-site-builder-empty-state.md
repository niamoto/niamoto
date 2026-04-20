# Site builder empty state and publish readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the automatic `Home` page from fresh/scaffolded site configs, restore `Site Setup` as the default entry for unconfigured projects, and block `Publish` until a real root page exists.

**Architecture:** Keep the site API literal: no synthetic `home/index.html` on read or save. Move readiness logic into two explicit places: backend pipeline status for global gating and a small frontend helper for Site Builder empty-state detection, including the legacy placeholder escape hatch. Publish stays driven by pipeline status and gets a direct CTA back to `/site/pages`.

**Tech Stack:** FastAPI routers, YAML config mutation, pytest, React 19, Vitest, React server-render/static tests, i18next JSON locales.

---

## File map

- Modify: `src/niamoto/gui/api/routers/site.py`
  - Stop injecting `_default_root_index_page()` during normalization and save.
- Modify: `src/niamoto/gui/api/routers/templates.py`
  - Stop creating `static_pages: [home]` in the default `html_page_exporter`.
- Modify: `src/niamoto/gui/api/services/templates/config_scaffold.py`
  - Stop creating `static_pages: [home]` when scaffolding `web_pages`.
- Modify: `src/niamoto/gui/api/routers/pipeline.py`
  - Compute site readiness from a real root page, not from exporter params alone.
  - Detect the legacy placeholder case.
- Modify: `tests/gui/api/routers/test_site.py`
  - Replace injection expectations with literal-empty expectations.
- Modify: `tests/gui/api/routers/test_templates.py`
  - Replace scaffold home-page expectation with `static_pages: []`.
- Modify: `tests/gui/api/routers/test_pipeline.py`
  - Cover empty root, legacy placeholder, and real configured site.
- Create: `src/niamoto/gui/ui/src/features/site/lib/siteReadiness.ts`
  - Pure frontend readiness helpers for empty config, publishable root detection, and legacy placeholder detection.
- Create: `src/niamoto/gui/ui/src/features/site/lib/siteReadiness.test.ts`
  - Unit tests for the helper.
- Create: `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.test.tsx`
  - Component regression for wizard rendering on empty persisted state and empty draft-after-delete state.
- Modify: `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx`
  - Use readiness helper instead of `static_pages.length === 0 && navigation.length === 0`.
  - Reopen the wizard immediately when the draft becomes unconfigured after deletion.
- Create: `src/niamoto/gui/ui/src/features/publish/lib/buildGate.ts`
  - Small pure helper for blocked publish/build copy and target route.
- Create: `src/niamoto/gui/ui/src/features/publish/lib/buildGate.test.ts`
  - Unit tests for the helper.
- Modify: `src/niamoto/gui/ui/src/features/publish/views/index.tsx`
  - Use the build-gate helper and add a direct CTA to `/site/pages`.
- Modify: `src/niamoto/gui/ui/src/i18n/locales/en/publish.json`
- Modify: `src/niamoto/gui/ui/src/i18n/locales/fr/publish.json`
  - Replace the “save once so directories are written” copy with true site-setup copy.

## Chunk 1: Make the site API literal again

### Task 1: Remove automatic home-page injection from `/api/site/config`

**Files:**
- Modify: `src/niamoto/gui/api/routers/site.py`
- Test: `tests/gui/api/routers/test_site.py`

- [ ] **Step 1: Replace the two router tests that currently encode the wrong behavior**

In `tests/gui/api/routers/test_site.py`, replace the two “adds/injects default home page” tests with these exact tests:

```python
def test_get_site_config_keeps_empty_static_pages_when_missing(self):
    with tempfile.TemporaryDirectory() as temp_dir:
        project = Path(temp_dir)
        config_dir = project / "config"
        _write_config(
            config_dir / "export.yml",
            {
                "exports": [
                    {
                        "name": "web_pages",
                        "enabled": True,
                        "exporter": "html_page_exporter",
                        "params": {"navigation": []},
                        "static_pages": [],
                        "groups": [],
                    }
                ]
            },
        )

        with patch(
            "niamoto.gui.api.routers.site.get_working_directory",
            return_value=project,
        ):
            app = create_app()
            client = TestClient(app)
            response = client.get("/api/site/config")
            assert response.status_code == 200, response.text

        data = response.json()
        assert data["static_pages"] == []


def test_update_site_config_persists_empty_static_pages(self):
    with tempfile.TemporaryDirectory() as temp_dir:
        project = Path(temp_dir)
        config_dir = project / "config"
        _write_config(config_dir / "export.yml", {"exports": []})

        payload = {
            "site": {"title": "Niamoto", "lang": "fr"},
            "navigation": [],
            "footer_navigation": [],
            "static_pages": [],
        }

        with patch(
            "niamoto.gui.api.routers.site.get_working_directory",
            return_value=project,
        ):
            app = create_app()
            client = TestClient(app)
            response = client.put("/api/site/config", json=payload)
            assert response.status_code == 200, response.text

        saved_config = yaml.safe_load((config_dir / "export.yml").read_text())
        web_pages = saved_config["exports"][0]
        assert web_pages["static_pages"] == []
```

- [ ] **Step 2: Run the router tests and verify they fail before the implementation**

Run:

```bash
uv run pytest tests/gui/api/routers/test_site.py -q
```

Expected: FAIL on the two new tests because the current router still injects `home/index.html`.

- [ ] **Step 3: Remove the injection logic in `site.py`**

Make these exact edits in `src/niamoto/gui/api/routers/site.py`:

```python
def _normalize_static_pages(
    static_pages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    normalized_pages: list[dict[str, Any]] = []
    output_aliases: dict[str, str] = {}

    for page in static_pages:
        normalized_page = dict(page)
        current_output = _normalize_output_alias(
            str(normalized_page.get("output_file", ""))
        )

        if _is_root_index_page(normalized_page):
            normalized_page["output_file"] = _ROOT_INDEX_OUTPUT
            if current_output and current_output != _ROOT_INDEX_OUTPUT:
                output_aliases[current_output] = _ROOT_INDEX_OUTPUT
        elif current_output is not None:
            normalized_page["output_file"] = current_output

        normalized_pages.append(normalized_page)

    return normalized_pages, output_aliases
```

And in `update_site_config()`, change the `web_pages` bootstrap from:

```python
"static_pages": [_default_root_index_page()],
```

to:

```python
"static_pages": [],
```

Then delete `_default_root_index_page()` entirely if nothing else uses it.

- [ ] **Step 4: Re-run the router tests**

Run:

```bash
uv run pytest tests/gui/api/routers/test_site.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/niamoto/gui/api/routers/site.py tests/gui/api/routers/test_site.py
git commit -m "fix: remove default home injection from site config"
```

---

### Task 2: Remove automatic home-page creation from scaffold/default exporter paths

**Files:**
- Modify: `src/niamoto/gui/api/routers/templates.py`
- Modify: `src/niamoto/gui/api/services/templates/config_scaffold.py`
- Test: `tests/gui/api/routers/test_templates.py`

- [ ] **Step 1: Replace the scaffold regression test**

In `tests/gui/api/routers/test_templates.py`, replace the existing home-page scaffold expectation with this test:

```python
def test_scaffold_keeps_web_export_without_default_home_page(self, test_work_dir):
    from niamoto.gui.api.services.templates.config_scaffold import scaffold_configs

    changed, _ = scaffold_configs(Path(test_work_dir))
    assert changed is True

    with open(
        Path(test_work_dir) / "config" / "export.yml", "r", encoding="utf-8"
    ) as f:
        export_config = yaml.safe_load(f) or {}

    web_export = next(
        export
        for export in export_config.get("exports", [])
        if export.get("name") == "web_pages"
    )
    assert web_export["static_pages"] == []
```

- [ ] **Step 2: Run the scaffold tests and capture the expected failure**

Run:

```bash
uv run pytest tests/gui/api/routers/test_templates.py -q
```

Expected: FAIL on the new scaffold assertion because scaffold still writes `home/index.html`.

- [ ] **Step 3: Remove the default `static_pages` list from both creation paths**

Apply these exact changes:

In `src/niamoto/gui/api/services/templates/config_scaffold.py`, change:

```python
"static_pages": [
    {
        "name": "home",
        "template": "index.html",
        "output_file": "index.html",
    }
],
```

to:

```python
"static_pages": [],
```

In `src/niamoto/gui/api/routers/templates.py`, change:

```python
"static_pages": [
    {
        "name": "home",
        "template": "index.html",
        "output_file": "index.html",
    }
],
```

to:

```python
"static_pages": [],
```

- [ ] **Step 4: Re-run the scaffold tests**

Run:

```bash
uv run pytest tests/gui/api/routers/test_templates.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/niamoto/gui/api/routers/templates.py src/niamoto/gui/api/services/templates/config_scaffold.py tests/gui/api/routers/test_templates.py
git commit -m "fix: stop scaffolding a synthetic home page"
```

---

## Chunk 2: Recompute readiness from a real root page

### Task 3: Make pipeline site status depend on a real root page, with legacy-placeholder escape hatch

**Files:**
- Modify: `src/niamoto/gui/api/routers/pipeline.py`
- Test: `tests/gui/api/routers/test_pipeline.py`

- [ ] **Step 1: Add failing pipeline tests for the new readiness rules**

Append these tests to `tests/gui/api/routers/test_pipeline.py`:

```python
def test_pipeline_site_is_unconfigured_when_web_export_has_no_root_page(
    tmp_path, monkeypatch
):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    db_dir = work_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "transform.yml").write_text("[]\n")
    (config_dir / "export.yml").write_text(
        """
exports:
  - name: web_pages
    enabled: true
    exporter: html_page_exporter
    params:
      template_dir: templates/
      output_dir: exports/web
      site:
        title: Test
        lang: fr
    static_pages: []
    groups: []
""".strip()
    )

    monkeypatch.setattr(pipeline_router, "get_working_directory", lambda: work_dir)
    monkeypatch.setattr(
        pipeline_router, "get_database_path", lambda: db_dir / "niamoto.duckdb"
    )

    class DummyStore:
        def get_running_job(self):
            return None

        def get_last_run(self, *args, **kwargs):
            return None

    app = FastAPI()
    app.state.job_store = DummyStore()
    app.state.job_store_work_dir = work_dir
    monkeypatch.setattr(
        pipeline_router, "resolve_job_store", lambda app: app.state.job_store
    )

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/pipeline/status",
            "headers": [],
            "app": app,
        }
    )

    response = asyncio.run(pipeline_router.get_pipeline_status(request))
    assert response.site.status == "unconfigured"


def test_pipeline_site_treats_legacy_placeholder_home_as_unconfigured(
    tmp_path, monkeypatch
):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    db_dir = work_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "transform.yml").write_text("[]\n")
    (config_dir / "export.yml").write_text(
        """
exports:
  - name: web_pages
    enabled: true
    exporter: html_page_exporter
    params:
      template_dir: templates/
      output_dir: exports/web
      site:
        title: Test
        lang: fr
      navigation: []
      footer_navigation: []
    static_pages:
      - name: home
        template: index.html
        output_file: index.html
    groups: []
""".strip()
    )

    monkeypatch.setattr(pipeline_router, "get_working_directory", lambda: work_dir)
    monkeypatch.setattr(
        pipeline_router, "get_database_path", lambda: db_dir / "niamoto.duckdb"
    )

    class DummyStore:
        def get_running_job(self):
            return None

        def get_last_run(self, *args, **kwargs):
            return None

    app = FastAPI()
    app.state.job_store = DummyStore()
    app.state.job_store_work_dir = work_dir
    monkeypatch.setattr(
        pipeline_router, "resolve_job_store", lambda app: app.state.job_store
    )

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/pipeline/status",
            "headers": [],
            "app": app,
        }
    )

    response = asyncio.run(pipeline_router.get_pipeline_status(request))
    assert response.site.status == "unconfigured"


def test_pipeline_site_is_fresh_when_root_page_and_navigation_exist(
    tmp_path, monkeypatch
):
    work_dir = tmp_path / "project"
    config_dir = work_dir / "config"
    db_dir = work_dir / "db"
    config_dir.mkdir(parents=True)
    db_dir.mkdir(parents=True)

    (config_dir / "transform.yml").write_text("[]\n")
    (config_dir / "export.yml").write_text(
        """
exports:
  - name: web_pages
    enabled: true
    exporter: html_page_exporter
    params:
      template_dir: templates/
      output_dir: exports/web
      site:
        title: Test
        lang: fr
      navigation:
        - text: Home
          url: /index.html
    static_pages:
      - name: home
        template: index.html
        output_file: index.html
    groups: []
""".strip()
    )

    monkeypatch.setattr(pipeline_router, "get_working_directory", lambda: work_dir)
    monkeypatch.setattr(
        pipeline_router, "get_database_path", lambda: db_dir / "niamoto.duckdb"
    )

    class DummyStore:
        def get_running_job(self):
            return None

        def get_last_run(self, *args, **kwargs):
            return None

    app = FastAPI()
    app.state.job_store = DummyStore()
    app.state.job_store_work_dir = work_dir
    monkeypatch.setattr(
        pipeline_router, "resolve_job_store", lambda app: app.state.job_store
    )

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/pipeline/status",
            "headers": [],
            "app": app,
        }
    )

    response = asyncio.run(pipeline_router.get_pipeline_status(request))
    assert response.site.status == "fresh"
```

- [ ] **Step 2: Run the pipeline tests first**

Run:

```bash
uv run pytest tests/gui/api/routers/test_pipeline.py -q
```

Expected: FAIL on the new readiness tests because site status still treats valid exporter params as sufficient.

- [ ] **Step 3: Implement explicit readiness helpers in `pipeline.py`**

Add these helpers near `_has_valid_site_export_params()` in `src/niamoto/gui/api/routers/pipeline.py`:

```python
def _normalize_output_alias(path: str | None) -> str:
    return (path or "").strip().lstrip("/")


def _navigation_has_url(items: list[dict], target: str) -> bool:
    for item in items:
        if item.get("url") == target:
            return True
        if _navigation_has_url(item.get("children", []) or [], target):
            return True
    return False


def _footer_has_url(sections: list[dict], target: str) -> bool:
    for section in sections:
        for link in section.get("links", []) or []:
            if link.get("url") == target:
                return True
    return False


def _has_root_static_page(static_pages: list[dict]) -> bool:
    return any(
        _normalize_output_alias(str(page.get("output_file", ""))) == "index.html"
        or page.get("template") == "index.html"
        for page in static_pages
    )


def _is_legacy_placeholder_site(export_entry: dict) -> bool:
    static_pages = export_entry.get("static_pages", []) or []
    if len(static_pages) != 1:
        return False

    page = static_pages[0]
    if str(page.get("name", "")).lower() != "home":
        return False
    if page.get("template") != "index.html":
        return False
    if _normalize_output_alias(str(page.get("output_file", ""))) != "index.html":
        return False
    if page.get("context"):
        return False

    params = export_entry.get("params", {}) or {}
    navigation = params.get("navigation", []) or []
    footer_navigation = params.get("footer_navigation", []) or []
    return not _navigation_has_url(navigation, "/index.html") and not _footer_has_url(
        footer_navigation, "/index.html"
    )


def _has_publishable_site(export_entry: dict) -> bool:
    static_pages = export_entry.get("static_pages", []) or []
    return _has_root_static_page(static_pages) and not _is_legacy_placeholder_site(
        export_entry
    )
```

Then update the site-status branch in `get_pipeline_status()` to:

```python
if exp.get("exporter") == "html_page_exporter" and exp.get("enabled", True):
    if _has_valid_site_export_params(exp) and _has_publishable_site(exp):
        site_configured = True
        break
    site_unconfigured = True
```

And in `_get_site_summary()`, stop counting the legacy placeholder as a real page:

```python
page_count = 0 if _is_legacy_placeholder_site(exp) else (
    len(static_pages) if isinstance(static_pages, list) else 0
)
```

- [ ] **Step 4: Re-run the pipeline tests**

Run:

```bash
uv run pytest tests/gui/api/routers/test_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/niamoto/gui/api/routers/pipeline.py tests/gui/api/routers/test_pipeline.py
git commit -m "fix: base site readiness on a real root page"
```

---

## Chunk 3: Restore Site Setup as the real empty state

### Task 4: Add a frontend site-readiness helper and route `SiteBuilder` through it

**Files:**
- Create: `src/niamoto/gui/ui/src/features/site/lib/siteReadiness.ts`
- Create: `src/niamoto/gui/ui/src/features/site/lib/siteReadiness.test.ts`
- Create: `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.test.tsx`
- Modify: `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx`

- [ ] **Step 1: Add failing frontend unit tests for readiness classification**

Create `src/niamoto/gui/ui/src/features/site/lib/siteReadiness.test.ts` with:

```ts
import { describe, expect, it } from 'vitest'
import {
  hasPublishableRootPage,
  isLegacyPlaceholderSite,
  requiresSiteSetup,
} from './siteReadiness'

describe('siteReadiness', () => {
  it('requires setup when static pages are empty', () => {
    expect(
      requiresSiteSetup({
        static_pages: [],
        navigation: [],
        footer_navigation: [],
      })
    ).toBe(true)
  })

  it('treats the legacy placeholder home as unconfigured', () => {
    expect(
      isLegacyPlaceholderSite({
        static_pages: [
          { name: 'home', template: 'index.html', output_file: 'index.html' },
        ],
        navigation: [],
        footer_navigation: [],
      })
    ).toBe(true)
  })

  it('recognizes a real configured root page when the home is linked', () => {
    expect(
      hasPublishableRootPage([
        { name: 'home', template: 'index.html', output_file: 'index.html' },
      ])
    ).toBe(true)

    expect(
      requiresSiteSetup({
        static_pages: [
          { name: 'home', template: 'index.html', output_file: 'index.html' },
        ],
        navigation: [{ text: 'Home', url: '/index.html' }],
        footer_navigation: [],
      })
    ).toBe(false)
  })
})
```

- [ ] **Step 2: Run the new frontend test first**

Run:

```bash
cd src/niamoto/gui/ui && pnpm test -- src/features/site/lib/siteReadiness.test.ts
```

Expected: FAIL because the helper file does not exist yet.

- [ ] **Step 3: Implement the pure helper**

Create `src/niamoto/gui/ui/src/features/site/lib/siteReadiness.ts` with:

```ts
import {
  getCanonicalStaticPageOutputFile,
  type FooterSection,
  type NavigationItem,
  type SiteConfigResponse,
  type StaticPage,
} from '@/shared/hooks/useSiteConfig'

type SiteLike = Pick<SiteConfigResponse, 'static_pages' | 'navigation' | 'footer_navigation'>

function navigationHasUrl(items: NavigationItem[], target: string): boolean {
  return items.some((item) =>
    item.url === target || navigationHasUrl(item.children ?? [], target)
  )
}

function footerHasUrl(sections: FooterSection[], target: string): boolean {
  return sections.some((section) => section.links.some((link) => link.url === target))
}

export function hasPublishableRootPage(pages: StaticPage[]): boolean {
  return pages.some((page) => getCanonicalStaticPageOutputFile(page) === 'index.html')
}

export function isLegacyPlaceholderSite(site: SiteLike): boolean {
  if (site.static_pages.length !== 1) return false

  const [page] = site.static_pages
  if (page.name.toLowerCase() !== 'home') return false
  if (page.template !== 'index.html') return false
  if (getCanonicalStaticPageOutputFile(page) !== 'index.html') return false
  if (page.context && Object.keys(page.context).length > 0) return false

  return !navigationHasUrl(site.navigation, '/index.html') &&
    !footerHasUrl(site.footer_navigation, '/index.html')
}

export function requiresSiteSetup(site: SiteLike): boolean {
  if (site.static_pages.length === 0) return true
  if (!hasPublishableRootPage(site.static_pages)) return true
  return isLegacyPlaceholderSite(site)
}
```

- [ ] **Step 4: Add a SiteBuilder regression test for empty persisted state and empty draft state**

Create `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.test.tsx` with:

```tsx
import { describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { SiteBuilder } from './SiteBuilder'

const stateRef = {
  value: null as any,
}

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (_key: string, defaultValue?: string) => defaultValue ?? 'Site setup',
    i18n: { language: 'fr', resolvedLanguage: 'fr' },
  }),
}))

vi.mock('../hooks/useSiteBuilderState', () => ({
  useSiteBuilderState: () => stateRef.value,
}))

vi.mock('@/shared/hooks/useSiteConfig', () => ({
  useFileContent: () => ({ data: null }),
  useGroupIndexPreview: () => ({ mutate: vi.fn(), isPending: false }),
  isRootIndexTemplate: (template?: string | null) => template === 'index.html',
}))

vi.mock('./SiteSetupWizard', () => ({
  SiteSetupWizard: () => <div>Site setup</div>,
}))

vi.mock('./PagesOverview', () => ({
  PagesOverview: () => <div>Pages overview</div>,
}))

vi.mock('./UnifiedSiteTree', () => ({
  UnifiedSiteTree: () => <div>Tree</div>,
}))

vi.mock('./SiteBuilderPreview', () => ({
  SitePreview: () => <div>Preview</div>,
  GroupIndexPreviewPanel: () => <div>Group preview</div>,
}))

function buildState(overrides: Record<string, unknown> = {}) {
  return {
    siteConfig: {
      site: { title: 'Niamoto', lang: 'fr', languages: ['fr'], primary_color: '#228b22', nav_color: '#ffffff' },
      navigation: [],
      footer_navigation: [],
      static_pages: [],
      template_dir: 'templates/',
      output_dir: 'exports/web',
      copy_assets_from: [],
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    groupsLoading: false,
    groups: [],
    availableNewPageTemplates: [],
    unifiedTree: [],
    setUnifiedTree: vi.fn(),
    allPages: [],
    setAllPages: vi.fn(),
    editedNavigation: [],
    editedPages: [],
    editedSite: { title: 'Niamoto', lang: 'fr', languages: ['fr'], primary_color: '#228b22', nav_color: '#ffffff' },
    setEditedSite: vi.fn(),
    editedFooterNavigation: [],
    setEditedFooterNavigation: vi.fn(),
    selection: null,
    setSelection: vi.fn(),
    pageToDelete: null,
    setPageToDelete: vi.fn(),
    hasChanges: false,
    hasExistingHomePage: false,
    isSaving: false,
    isEnablingIndexPage: false,
    handleSave: vi.fn(),
    saveConfig: vi.fn(),
    handleAddPage: vi.fn(),
    handleTemplateSelected: vi.fn(),
    handleCreatePageFromNavigation: vi.fn(),
    handleUpdatePage: vi.fn(),
    handleDeletePage: vi.fn(),
    confirmDeletePage: vi.fn(),
    handleDuplicatePage: vi.fn(),
    handleAddPageToNavigation: vi.fn(),
    handleEnableGroupIndexPage: vi.fn(),
    isPageInMenu: vi.fn(() => false),
    togglePageInMenu: vi.fn(),
    findMenuRefsForPage: vi.fn(() => []),
    findMenuRefsForCollection: vi.fn(() => []),
    updateMenuItemLabel: vi.fn(),
    removeMenuItem: vi.fn(),
    addPageToMenu: vi.fn(),
    addCollectionToMenu: vi.fn(),
    toggleItemVisibility: vi.fn(),
    addExternalLink: vi.fn(),
    removeExternalLink: vi.fn(),
    updateExternalLink: vi.fn(),
    ...overrides,
  }
}

describe('SiteBuilder empty-state regressions', () => {
  it('renders Site Setup for an empty persisted config', () => {
    stateRef.value = buildState()
    const html = renderToStaticMarkup(<SiteBuilder />)
    expect(html).toContain('Site setup')
  })

  it('renders Site Setup again when the draft becomes empty after deleting home', () => {
    stateRef.value = buildState({
      siteConfig: {
        site: { title: 'Niamoto', lang: 'fr', languages: ['fr'], primary_color: '#228b22', nav_color: '#ffffff' },
        navigation: [{ text: 'Home', url: '/index.html' }],
        footer_navigation: [],
        static_pages: [{ name: 'home', template: 'index.html', output_file: 'index.html' }],
        template_dir: 'templates/',
        output_dir: 'exports/web',
        copy_assets_from: [],
      },
      editedNavigation: [],
      editedPages: [],
      hasChanges: true,
    })

    const html = renderToStaticMarkup(<SiteBuilder />)
    expect(html).toContain('Site setup')
  })
})
```

- [ ] **Step 5: Use the helper inside `SiteBuilder.tsx`**

In `src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx`, add:

```ts
import { requiresSiteSetup } from '../lib/siteReadiness'
```

Replace the old empty-state block:

```ts
const isSiteEmpty = state.siteConfig &&
  state.siteConfig.static_pages.length === 0 &&
  state.siteConfig.navigation.length === 0
```

with:

```ts
const persistedSiteNeedsSetup = state.siteConfig
  ? requiresSiteSetup(state.siteConfig)
  : true

const draftSiteNeedsSetup = requiresSiteSetup({
  static_pages: state.editedPages,
  navigation: state.editedNavigation,
  footer_navigation: state.editedFooterNavigation,
})

const siteNeedsSetup = state.hasChanges ? draftSiteNeedsSetup : persistedSiteNeedsSetup
```

Then add a reset effect:

```ts
useEffect(() => {
  if (siteNeedsSetup) {
    setWizardDismissed(false)
  }
}, [siteNeedsSetup])
```

And update the wizard conditions from `isSiteEmpty` to `siteNeedsSetup`:

```ts
const editorTransitionKey = state.selection
  ? `${state.selection.type}:${state.selection.id ?? ''}:${previewEnabled ? 'preview' : 'editor'}`
  : `${overviewPreview ? 'overview-preview' : showWizard || (siteNeedsSetup && !wizardDismissed) ? 'wizard' : 'overview'}:${previewEnabled ? 'preview' : 'editor'}`

if ((!state.selection && siteNeedsSetup && !wizardDismissed) || showWizard) {
  return (
    <SiteSetupWizard
      groups={state.groups}
      editedSite={state.editedSite}
      onComplete={handleWizardComplete}
      onSetEditedSite={state.setEditedSite}
    />
  )
}
```

- [ ] **Step 6: Re-run the focused frontend tests and a targeted build**

Run:

```bash
cd src/niamoto/gui/ui && pnpm test -- src/features/site/lib/siteReadiness.test.ts src/features/site/components/SiteBuilder.test.tsx
```

Expected: PASS.

Then run:

```bash
cd src/niamoto/gui/ui && pnpm build
```

Expected: build succeeds with no TypeScript errors in `SiteBuilder.tsx`.

- [ ] **Step 7: Commit**

```bash
git add src/niamoto/gui/ui/src/features/site/lib/siteReadiness.ts src/niamoto/gui/ui/src/features/site/lib/siteReadiness.test.ts src/niamoto/gui/ui/src/features/site/components/SiteBuilder.test.tsx src/niamoto/gui/ui/src/features/site/components/SiteBuilder.tsx
git commit -m "fix: restore site setup for unconfigured sites"
```

---

## Chunk 4: Block Publish until a real site exists

### Task 5: Add a tested build-gate helper and a CTA back to Site Builder

**Files:**
- Create: `src/niamoto/gui/ui/src/features/publish/lib/buildGate.ts`
- Create: `src/niamoto/gui/ui/src/features/publish/lib/buildGate.test.ts`
- Modify: `src/niamoto/gui/ui/src/features/publish/views/index.tsx`
- Modify: `src/niamoto/gui/ui/src/i18n/locales/en/publish.json`
- Modify: `src/niamoto/gui/ui/src/i18n/locales/fr/publish.json`

- [ ] **Step 1: Add failing helper tests for the blocked publish state**

Create `src/niamoto/gui/ui/src/features/publish/lib/buildGate.test.ts` with:

```ts
import { describe, expect, it } from 'vitest'
import { getBuildGate } from './buildGate'

describe('getBuildGate', () => {
  it('blocks generation when the site is unconfigured', () => {
    expect(getBuildGate('unconfigured')).toEqual({
      blocked: true,
      titleKey: 'build.configurationRequiredTitle',
      descriptionKey: 'build.configurationRequired',
      ctaKey: 'build.goToSiteBuilder',
      ctaPath: '/site/pages',
    })
  })

  it('blocks generation when the site has never been configured', () => {
    expect(getBuildGate('never_run').blocked).toBe(true)
  })

  it('allows generation when the site is fresh', () => {
    expect(getBuildGate('fresh').blocked).toBe(false)
  })
})
```

- [ ] **Step 2: Run the new test first**

Run:

```bash
cd src/niamoto/gui/ui && pnpm test -- src/features/publish/lib/buildGate.test.ts
```

Expected: FAIL because the helper file does not exist yet.

- [ ] **Step 3: Implement the helper and wire it into the publish view**

Create `src/niamoto/gui/ui/src/features/publish/lib/buildGate.ts` with:

```ts
import type { FreshnessStatus } from '@/hooks/usePipelineStatus'

export function getBuildGate(siteStatus: FreshnessStatus | undefined) {
  const blocked = siteStatus === 'unconfigured' || siteStatus === 'never_run'

  return {
    blocked,
    titleKey: 'build.configurationRequiredTitle',
    descriptionKey: 'build.configurationRequired',
    ctaKey: 'build.goToSiteBuilder',
    ctaPath: '/site/pages',
  }
}
```

Then in `src/niamoto/gui/ui/src/features/publish/views/index.tsx`:

1. change the router import to:

```ts
import { useNavigate, useSearchParams } from 'react-router-dom'
```

2. add:

```ts
import { getBuildGate } from '@/features/publish/lib/buildGate'
```

3. create the gate state near `siteStatus`:

```ts
const navigate = useNavigate()
const buildGate = getBuildGate(siteStatus)
const siteBuildBlocked = buildGate.blocked
const buildBlockedTitle = t(buildGate.titleKey, 'Site configuration required')
const buildBlockedDescription = t(
  buildGate.descriptionKey,
  'Configure the site in Site Builder before launching a generation.'
)
```

4. remove the old `configurationIncomplete` branch entirely.

5. in the blocked alert/card action area, add:

```tsx
<Button
  variant="outline"
  size="sm"
  onClick={() => navigate(buildGate.ctaPath)}
>
  {t(buildGate.ctaKey, 'Open Site Builder')}
</Button>
```

- [ ] **Step 4: Update the locale strings**

In `src/niamoto/gui/ui/src/i18n/locales/en/publish.json`, replace:

```json
"configurationRequired": "Complete and save the site configuration before launching a generation.",
"configurationIncomplete": "The site configuration is incomplete. Save the site once so template and output directories are written before generating."
```

with:

```json
"configurationRequired": "Configure the site in Site Builder before launching a generation.",
"goToSiteBuilder": "Open Site Builder"
```

In `src/niamoto/gui/ui/src/i18n/locales/fr/publish.json`, replace:

```json
"configurationRequired": "Complétez et enregistrez la configuration du site avant de lancer une génération.",
"configurationIncomplete": "La configuration du site est incomplète. Enregistrez le site une fois pour écrire les répertoires de templates et de sortie avant de générer."
```

with:

```json
"configurationRequired": "Configurez d'abord le site dans le Site Builder avant de lancer une génération.",
"goToSiteBuilder": "Ouvrir le Site Builder"
```

- [ ] **Step 5: Re-run the focused frontend test and the dashboard regression**

Run:

```bash
cd src/niamoto/gui/ui && pnpm test -- src/features/publish/lib/buildGate.test.ts src/features/dashboard/components/dashboardRedesign.test.tsx
```

Expected: PASS.

Then run:

```bash
cd src/niamoto/gui/ui && pnpm build
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/niamoto/gui/ui/src/features/publish/lib/buildGate.ts src/niamoto/gui/ui/src/features/publish/lib/buildGate.test.ts src/niamoto/gui/ui/src/features/publish/views/index.tsx src/niamoto/gui/ui/src/i18n/locales/en/publish.json src/niamoto/gui/ui/src/i18n/locales/fr/publish.json
git commit -m "fix: block publish until the site is configured"
```

---

## Chunk 5: Final verification

### Task 6: Run the focused regression suite end-to-end

**Files:**
- No code changes

- [ ] **Step 1: Run the backend regression slice**

Run:

```bash
uv run pytest tests/gui/api/routers/test_site.py tests/gui/api/routers/test_templates.py tests/gui/api/routers/test_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 2: Run the frontend regression slice**

Run:

```bash
cd src/niamoto/gui/ui && pnpm test -- src/features/site/lib/siteReadiness.test.ts src/features/site/components/SiteBuilder.test.tsx src/features/publish/lib/buildGate.test.ts src/features/dashboard/components/dashboardRedesign.test.tsx
```

Expected: PASS.

- [ ] **Step 3: Run the frontend production build**

Run:

```bash
cd src/niamoto/gui/ui && pnpm build
```

Expected: PASS.

- [ ] **Step 4: Sanity-check the user-visible outcomes manually**

Checklist:

- [ ] Fresh project: `/site/pages` opens `Site Setup`
- [ ] Fresh project: `/publish` disables generation and shows “Open Site Builder”
- [ ] Existing legacy placeholder project: `/site/pages` opens `Site Setup`
- [ ] Existing legacy placeholder project: `/publish` disables generation
- [ ] Configured site with real `Home`: `/publish` enables generation
- [ ] Deleting the last root page sends the Site module back to setup

No commit for this task unless you had to patch a missed bug during verification.

---

## Completion criteria

- [ ] No backend path injects or recreates `home/index.html`
- [ ] Scaffold/default exporter creation leaves `static_pages: []`
- [ ] Pipeline site status is `unconfigured` without a real root page
- [ ] Legacy placeholder projects are treated as unconfigured
- [ ] `SiteBuilder` reopens `Site Setup` for empty and post-delete states
- [ ] `Publish` stays blocked until a real root page exists
