/**
 * Groups List - Overview of all reference groups for widget configuration
 * Route: /groups
 */

import { useNavigate } from 'react-router-dom'
import { useReferences } from '@/hooks/useReferences'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Layers, ArrowRight } from 'lucide-react'

export default function GroupsPage() {
  const navigate = useNavigate()
  const { data: referencesData, isLoading } = useReferences()
  const references = referencesData?.references ?? []

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Chargement...</div>
      </div>
    )
  }

  if (references.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center max-w-md">
          <Layers className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h2 className="text-lg font-medium">Aucun groupe disponible</h2>
          <p className="text-muted-foreground mt-2">
            Importez d'abord des références pour pouvoir configurer leurs widgets.
          </p>
          <button
            className="mt-4 text-primary hover:underline"
            onClick={() => navigate('/sources/import')}
          >
            Importer des données
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Groupes</h1>
        <p className="text-muted-foreground mt-1">
          Configurez les widgets et transformations pour chaque groupe de référence.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {references.map((ref) => (
          <Card
            key={ref.name}
            className="cursor-pointer hover:border-primary transition-colors"
            onClick={() => navigate(`/groups/${ref.name}`)}
          >
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{ref.name}</CardTitle>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
              </div>
              <CardDescription>
                Table: {ref.table_name}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Badge variant="outline">{ref.kind}</Badge>
                {ref.entity_count !== undefined && (
                  <Badge variant="secondary">{ref.entity_count} entités</Badge>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
