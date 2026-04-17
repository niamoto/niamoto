# Export and Publish Workflow

The desktop app splits export work between the site area and the publish area:

- site configuration
- local and exported-site preview
- publish/build operations

## Entry points

- `src/niamoto/gui/ui/src/features/site`
- `src/niamoto/gui/ui/src/features/publish`
- `src/niamoto/gui/ui/src/features/site/components/SiteBuilderPreview.tsx`
- `src/niamoto/gui/ui/src/features/publish/views/index.tsx`
- `src/niamoto/gui/ui/src/features/publish/views/deployPlatformConfig.tsx`

## Site area

Use the site area for:

- navigation
- pages
- appearance
- content editing
- references between content and generated collection pages
- in-context preview while editing templates and pages

## Publish area

Use the publish area for:

- preview of the generated exported site
- build status
- deployment-oriented actions
- generated output lifecycle
- deployment destinations and credentials

## Typical workflow

Most projects follow this order:

1. Import and configure data
2. Configure collections and widgets
3. Configure the site
4. Preview the result
5. Build and publish

## Supported deployment targets

The current product exposes these publish destinations:

- Cloudflare Workers
- GitHub Pages
- Netlify
- Vercel
- Render
- SSH / rsync

The CLI and the GUI surface the same deployment targets today.
