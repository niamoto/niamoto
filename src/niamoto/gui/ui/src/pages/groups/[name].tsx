/**
 * Group Configuration Page - Configure widgets for a reference group
 * Route: /groups/:name
 */

import { useParams, useNavigate } from 'react-router-dom'
import { useReferences } from '@/hooks/useReferences'
import { GroupPanel } from '@/components/panels/GroupPanel'

export default function GroupDetailPage() {
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const { data: referencesData, isLoading } = useReferences()
  const references = referencesData?.references ?? []

  const reference = references.find((r) => r.name === name)

  // Show loading state while fetching
  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Chargement...</div>
      </div>
    )
  }

  if (!reference) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-lg font-medium">Groupe non trouvé</h2>
          <p className="text-muted-foreground mt-1">
            Le groupe "{name}" n'existe pas.
          </p>
          <button
            className="mt-4 text-primary hover:underline"
            onClick={() => navigate('/groups')}
          >
            Retour aux groupes
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto">
      <GroupPanel reference={reference} />
    </div>
  )
}
