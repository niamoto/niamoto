const GROUPED_ROUTE_SURFACES = new Set([
  'sources',
  'groups',
  'site',
  'publish',
  'help',
])

export function getRouteSurfaceKey(pathname: string) {
  if (pathname === '/') {
    return '/'
  }

  const parts = pathname.split('/').filter(Boolean)
  const [section, subsection] = parts

  if (!section) {
    return '/'
  }

  if (GROUPED_ROUTE_SURFACES.has(section)) {
    return `/${section}`
  }

  if (section === 'tools' && subsection) {
    return `/tools/${subsection}`
  }

  return `/${section}`
}
