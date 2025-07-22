import { useImport } from './ImportContext'
import { useImportProgress } from './ImportProgressContext'
import { ImportStepCard } from './components/ImportStepCard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  FileSpreadsheet,
  TreePine,
  MapPin,
  Map,
  Database,
  Info,
  Globe
} from 'lucide-react'

export function SummaryStep() {
  const { state } = useImport()
  const { occurrences, plots, shapes } = state
  const { progress } = useImportProgress()


  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Résumé de votre import</h2>
        <p className="text-muted-foreground mt-2">
          Vérifiez les informations avant de lancer l'import
        </p>
      </div>

      {/* Import summary cards */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Occurrences card */}
        <ImportStepCard
          title="Occurrences"
          icon={<FileSpreadsheet className="w-5 h-5" />}
          status={progress.occurrences}
        >
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Fichier</span>
            <span className="text-sm font-medium">{occurrences.file?.name}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Lignes</span>
            <Badge variant="secondary">
              {occurrences.fileAnalysis?.rowCount ||
               occurrences.fileAnalysis?.row_count ||
               occurrences.fileAnalysis?.total_rows ||
               0}
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Champs mappés</span>
            <Badge variant="secondary">{Object.keys(occurrences.fieldMappings).length}</Badge>
          </div>
        </ImportStepCard>

        {/* Taxonomy card */}
        <ImportStepCard
          title="Taxonomie"
          icon={<TreePine className="w-5 h-5 text-green-600" />}
          status={progress.taxonomy}
          variant="success"
        >
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Niveaux</span>
            <Badge variant="secondary">{occurrences.taxonomyHierarchy.ranks.length}</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Hiérarchie</span>
            <span className="text-xs font-mono">
              {occurrences.taxonomyHierarchy.ranks.slice(0, 3).join(' → ')}
              {occurrences.taxonomyHierarchy.ranks.length > 3 && '...'}
            </span>
          </div>
          {occurrences.apiEnrichment?.enabled && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Enrichissement API</span>
              <div className="flex items-center gap-1">
                <Globe className="w-3 h-3 text-blue-600" />
                <span className="text-xs">Activé</span>
              </div>
            </div>
          )}
        </ImportStepCard>

        {/* Plots card */}
        {plots?.file && (
          <ImportStepCard
            title="Plots"
            icon={<MapPin className="w-5 h-5" />}
            status={progress.plots}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Fichier</span>
              <span className="text-sm font-medium">{plots.file.name}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Lignes</span>
              <Badge variant="secondary">
                {plots.fileAnalysis?.rowCount ||
                 plots.fileAnalysis?.row_count ||
                 plots.fileAnalysis?.total_rows ||
                 0}
              </Badge>
            </div>
            {plots.linkField && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Liaison</span>
                <span className="text-xs font-mono">{plots.linkField} ↔ {plots.occurrenceLinkField}</span>
              </div>
            )}
            {plots.hierarchy?.enabled && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Hiérarchie</span>
                <span className="text-xs">
                  {plots.hierarchy.levels.length} niveaux
                  {plots.hierarchy.aggregate_geometry && ' (géométries agrégées)'}
                </span>
              </div>
            )}
          </ImportStepCard>
        )}

        {/* Shapes card - Show overall progress if multiple shapes */}
        {shapes && shapes.length > 0 && (
          <ImportStepCard
            title="Shapes"
            icon={<Map className="w-5 h-5" />}
            status={progress.shapes && progress.shapes.length > 0 ? {
              status: progress.shapes.every(s => s.status === 'completed') ? 'completed' :
                     progress.shapes.some(s => s.status === 'failed') ? 'failed' :
                     progress.shapes.some(s => s.status === 'running') ? 'running' : 'pending',
              progress: progress.shapes.reduce((acc, s) => acc + s.progress, 0) / progress.shapes.length,
              count: progress.shapes.filter(s => s.status === 'completed').reduce((acc, s) => acc + (s.count || 0), 0)
            } : undefined}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Éléments total</span>
              <Badge variant="secondary">
                {shapes.reduce((total, shape) => total + (shape.fileAnalysis?.feature_count || 0), 0)}
              </Badge>
            </div>
            {shapes.map((shape, i) => shape.file && (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{shape.fieldMappings?.type || shape.type || `Shape ${i + 1}`}</span>
                <div className="flex items-center gap-2">
                  <span className="font-medium truncate max-w-[150px]">{shape.file.name}</span>
                  <span className="text-muted-foreground">
                    ({shape.fileAnalysis?.feature_count || 0} éléments)
                  </span>
                </div>
              </div>
            ))}
          </ImportStepCard>
        )}
      </div>

      {/* Process overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5" />
            Processus d'import
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="mt-0.5">
                <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-medium">
                  1
                </div>
              </div>
              <div className="flex-1">
                <div className="font-medium text-sm">Import des occurrences</div>
                <div className="text-sm text-muted-foreground">
                  Chargement des données d'observation et extraction automatique de la taxonomie
                  {occurrences.apiEnrichment?.enabled && ' avec enrichissement API'}
                </div>
              </div>
            </div>

            {plots?.file && (
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-medium">
                    2
                  </div>
                </div>
                <div className="flex-1">
                  <div className="font-medium text-sm">Import des plots</div>
                  <div className="text-sm text-muted-foreground">
                    Création des regroupements spatiaux et liaison avec les occurrences
                  </div>
                </div>
              </div>
            )}

            {shapes && shapes.length > 0 && (
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-medium">
                    {plots?.file ? 3 : 2}
                  </div>
                </div>
                <div className="flex-1">
                  <div className="font-medium text-sm">Import des shapes</div>
                  <div className="text-sm text-muted-foreground">
                    Chargement des zones géographiques pour l'analyse spatiale
                  </div>
                </div>
              </div>
            )}

          </div>
        </CardContent>
      </Card>

      {/* Import info */}
      <Alert>
        <Info className="w-4 h-4" />
        <AlertDescription>
          Une fois l'import lancé, le processus peut prendre quelques minutes selon
          la taille de vos données. Ne fermez pas cette fenêtre pendant l'import.
        </AlertDescription>
      </Alert>
    </div>
  )
}
