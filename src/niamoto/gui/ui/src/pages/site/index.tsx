/**
 * Site Configuration - Redirect to structure
 * Route: /site
 */

import { Navigate } from 'react-router-dom'

export default function SiteIndexPage() {
  return <Navigate to="/site/structure" replace />
}
