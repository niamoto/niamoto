import { useImport } from './ImportContext'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  FileSpreadsheet,
  TreePine,
  MapPin,
  Map,
  Database,
  BarChart3,
  Info,
  Globe
} from 'lucide-react'

export function SummaryStep() {
  const { state } = useImport()
  const { occurrences, plots, shapes, aggregationType } = state

  const getTaxonEstimate = () => {
    if (occurrences.fileAnalysis?.uniqueTaxonCount) {
      return `~${occurrences.fileAnalysis.uniqueTaxonCount} taxons uniques`
    }
    return 'Nombre de taxons à déterminer'
  }

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
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileSpreadsheet className="w-5 h-5" />
              Occurrences
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
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
          </CardContent>
        </Card>

        {/* Taxonomy card */}
        <Card className="border-green-200 bg-green-50/50 dark:bg-green-900/10">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TreePine className="w-5 h-5 text-green-600" />
              Taxonomie
              <Badge variant="secondary" className="ml-auto">Auto-extraite</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Estimation</span>
              <span className="text-sm font-medium">{getTaxonEstimate()}</span>
            </div>
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
          </CardContent>
        </Card>

        {/* Plots card */}
        {(aggregationType === 'plots' || aggregationType === 'both') && plots?.file && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <MapPin className="w-5 h-5" />
                Plots
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
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
            </CardContent>
          </Card>
        )}

        {/* Shapes card */}
        {(aggregationType === 'shapes' || aggregationType === 'both') && shapes && shapes.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Map className="w-5 h-5" />
                Shapes
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Nombre</span>
                <Badge variant="secondary">{shapes.length}</Badge>
              </div>
              {shapes.map((shape, i) => shape.file && (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">{shape.type || `Shape ${i + 1}`}</span>
                  <span className="font-medium truncate max-w-[150px]">{shape.file.name}</span>
                </div>
              ))}
            </CardContent>
          </Card>
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

            {(aggregationType === 'plots' || aggregationType === 'both') && (
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

            {(aggregationType === 'shapes' || aggregationType === 'both') && (
              <div className="flex items-start gap-3">
                <div className="mt-0.5">
                  <div className="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-xs font-medium">
                    {aggregationType === 'both' ? 3 : 2}
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

            <div className="flex items-start gap-3">
              <div className="mt-0.5">
                <div className="w-6 h-6 rounded-full bg-green-600 text-white flex items-center justify-center text-xs font-medium">
                  <BarChart3 className="w-3 h-3" />
                </div>
              </div>
              <div className="flex-1">
                <div className="font-medium text-sm">Génération des statistiques</div>
                <div className="text-sm text-muted-foreground">
                  Calcul automatique des métriques et indicateurs écologiques
                </div>
              </div>
            </div>
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
