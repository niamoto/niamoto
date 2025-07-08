import { useState, useEffect } from 'react'
import { useImportV2 } from './ImportContext'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { FileUpload } from '@/components/import-wizard/FileUpload'
import { ColumnMapper } from '@/components/import-wizard/ColumnMapper'
import { TaxonomyHierarchyEditor } from '@/components/import-wizard/TaxonomyHierarchyEditor'
import { ApiEnrichmentConfig, type ApiConfig } from '@/components/import-wizard/ApiEnrichmentConfig'
import { analyzeFile } from '@/lib/api/import'
import {
  FileSpreadsheet,
  TreePine,
  MapPin,
  Info,
  CheckCircle,
  AlertCircle,
  Globe,
  ArrowRight
} from 'lucide-react'

export function OccurrencesStep() {
  const { state, updateOccurrences } = useImportV2()
  const { occurrences } = state
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [activeTab, setActiveTab] = useState('upload')
  const [apiConfig, setApiConfig] = useState<ApiConfig>(
    occurrences.apiEnrichment || {
      enabled: false,
      plugin: 'api_taxonomy_enricher',
      api_url: '',
      auth_method: 'none',
      query_field: 'name',
      rate_limit: 10,
      cache_results: true,
      response_mapping: {}
    }
  )

  const handleFileSelect = async (file: File) => {
    updateOccurrences({ file, fileAnalysis: null, fieldMappings: {} })
    setIsAnalyzing(true)

    try {
      const analysis = await analyzeFile(file, 'occurrences')
      updateOccurrences({ fileAnalysis: analysis })

      // Auto-apply suggestions for required fields
      if (analysis.suggestions) {
        const autoMappings: Record<string, string> = {}
        if (analysis.suggestions.taxon_id?.[0]) {
          autoMappings.taxon_id = analysis.suggestions.taxon_id[0]
        }
        if (analysis.suggestions.location?.[0]) {
          autoMappings.location = analysis.suggestions.location[0]
        }
        updateOccurrences({ fieldMappings: autoMappings })
      }

      setActiveTab('mapping')
    } catch (error) {
      console.error('File analysis failed:', error)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleMappingComplete = (mappings: Record<string, string>) => {
    updateOccurrences({ fieldMappings: mappings })
  }

  const handleTaxonomyChange = ({ ranks, mappings }: { ranks: string[], mappings: Record<string, string> }) => {
    updateOccurrences({
      taxonomyHierarchy: { ranks, mappings },
      fieldMappings: { ...occurrences.fieldMappings, ...mappings }
    })
  }

  const handleApiConfigChange = (config: ApiConfig) => {
    setApiConfig(config)
    updateOccurrences({ apiEnrichment: config })
  }

  // Check if minimum requirements are met
  const hasRequiredFields = occurrences.fieldMappings.taxon_id && occurrences.fieldMappings.location
  const hasTaxonomyMapping = Object.keys(occurrences.taxonomyHierarchy.mappings).length >= 2

  // Pas de navigation automatique - l'utilisateur contrôle le flux

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <FileSpreadsheet className="w-6 h-6" />
          Données d'observation
        </h2>
        <p className="text-muted-foreground mt-2">
          Importez votre fichier d'occurrences. La taxonomie sera extraite automatiquement.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="upload" className="gap-2">
            1. Fichier
            {occurrences.file && <CheckCircle className="w-4 h-4" />}
          </TabsTrigger>
          <TabsTrigger value="mapping" disabled={!occurrences.file} className="gap-2">
            2. Champs requis
            {hasRequiredFields && <CheckCircle className="w-4 h-4" />}
          </TabsTrigger>
          <TabsTrigger value="taxonomy" disabled={!hasRequiredFields} className="gap-2">
            3. Taxonomie
            {hasTaxonomyMapping && <CheckCircle className="w-4 h-4" />}
          </TabsTrigger>
          <TabsTrigger value="enrichment" disabled={!hasTaxonomyMapping} className="gap-2">
            4. Enrichissement
            {apiConfig.enabled && <CheckCircle className="w-4 h-4" />}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upload" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Chargement du fichier</CardTitle>
              <CardDescription>
                Sélectionnez votre fichier CSV contenant les données d'observation
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FileUpload
                onFileSelect={handleFileSelect}
                acceptedFormats={['.csv']}
                isAnalyzing={isAnalyzing}
                maxSizeMB={100}
              />

              {occurrences.fileAnalysis && (
                <div className="mt-6 space-y-4">
                  <Alert>
                    <CheckCircle className="w-4 h-4" />
                    <AlertTitle>Analyse terminée</AlertTitle>
                    <AlertDescription>
                      <div className="mt-2 space-y-1">
                        <div>• {occurrences.fileAnalysis.rowCount || occurrences.fileAnalysis.row_count || occurrences.fileAnalysis.total_rows || 'N/A'} lignes détectées</div>
                        <div>• {occurrences.fileAnalysis.columns?.length} colonnes trouvées</div>
                        <div>• Encodage : {occurrences.fileAnalysis.encoding || 'UTF-8'}</div>
                      </div>
                    </AlertDescription>
                  </Alert>

                  {occurrences.fileAnalysis.preview && (
                    <div>
                      <h4 className="font-medium mb-2">Aperçu des données</h4>
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-border">
                          <thead>
                            <tr>
                              {occurrences.fileAnalysis.columns?.slice(0, 5).map((col: string) => (
                                <th key={col} className="px-3 py-2 text-left text-xs font-medium uppercase tracking-wider">
                                  {col}
                                </th>
                              ))}
                              {occurrences.fileAnalysis.columns?.length > 5 && (
                                <th className="px-3 py-2 text-center text-xs">...</th>
                              )}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border">
                            {occurrences.fileAnalysis.preview.slice(0, 3).map((row: any, i: number) => (
                              <tr key={i}>
                                {occurrences.fileAnalysis.columns?.slice(0, 5).map((col: string) => (
                                  <td key={col} className="px-3 py-2 text-sm">
                                    {row[col]}
                                  </td>
                                ))}
                                {occurrences.fileAnalysis.columns?.length > 5 && (
                                  <td className="px-3 py-2 text-center text-sm">...</td>
                                )}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Bouton Suivant */}
          {occurrences.file && (
            <div className="flex justify-end">
              <Button
                onClick={() => setActiveTab('mapping')}
                className="gap-2"
              >
                Suivant : Champs requis
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          )}
        </TabsContent>

        <TabsContent value="mapping" className="space-y-4">
          <Alert>
            <Info className="w-4 h-4" />
            <AlertDescription>
              Mappez uniquement les champs essentiels. La configuration de la hiérarchie taxonomique se fera à l'étape suivante.
            </AlertDescription>
          </Alert>

          <Card>
            <CardHeader>
              <CardTitle>Champs requis</CardTitle>
              <CardDescription>
                Ces champs sont nécessaires pour identifier et localiser vos observations
              </CardDescription>
            </CardHeader>
            <CardContent>
              {occurrences.fileAnalysis && (
                <ColumnMapper
                  importType="occurrences"
                  fileAnalysis={occurrences.fileAnalysis}
                  onMappingComplete={handleMappingComplete}
                />
              )}
            </CardContent>
          </Card>

          {/* Bouton Suivant */}
          {hasRequiredFields && (
            <div className="flex justify-end">
              <Button
                onClick={() => setActiveTab('taxonomy')}
                className="gap-2"
              >
                Suivant : Taxonomie
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          )}
        </TabsContent>

        <TabsContent value="taxonomy" className="space-y-4">
          <Alert className="border-green-200 bg-green-50 dark:bg-green-900/20">
            <TreePine className="w-4 h-4 text-green-600" />
            <AlertTitle>Extraction automatique de la taxonomie</AlertTitle>
            <AlertDescription>
              Configurez la hiérarchie taxonomique. Niamoto extraira automatiquement
              les taxons uniques de vos données selon cette configuration.
            </AlertDescription>
          </Alert>

          <TaxonomyHierarchyEditor
            ranks={occurrences.taxonomyHierarchy.ranks}
            fileColumns={occurrences.fileAnalysis?.columns || []}
            fieldMappings={occurrences.taxonomyHierarchy.mappings}
            onChange={handleTaxonomyChange}
          />

          {occurrences.fileAnalysis && hasTaxonomyMapping && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Aperçu de l'extraction</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">
                      {(() => {
                        // Estimer le nombre de taxons uniques basé sur le nombre de lignes
                        const totalRows = occurrences.fileAnalysis.rowCount ||
                                       occurrences.fileAnalysis.row_count ||
                                       occurrences.fileAnalysis.preview?.length || 0

                        // Si on a des données mais pas de rowCount, faire une estimation
                        const hasData = occurrences.fileAnalysis.preview && occurrences.fileAnalysis.preview.length > 0

                        if (!hasData && totalRows === 0) return 'Données en cours d\'analyse...'

                        // Estimation approximative : généralement 10-30% des lignes sont des taxons uniques
                        const estimatedRows = totalRows > 0 ? totalRows : (hasData ? 'plusieurs centaines de' : 0)
                        const estimatedUnique = typeof estimatedRows === 'number' ? Math.round(estimatedRows * 0.2) : 100

                        if (typeof estimatedRows !== 'number') return `Probablement ${estimatedRows} taxons`
                        if (estimatedUnique < 10) return '< 10 taxons estimés'
                        if (estimatedUnique > 1000) return `~${Math.round(estimatedUnique / 100) * 100} taxons estimés`
                        return `~${Math.round(estimatedUnique / 10) * 10} taxons estimés`
                      })()}
                    </Badge>
                  </div>
                  <div className="text-sm text-muted-foreground space-y-1">
                    <p>
                      Hiérarchie configurée : {Object.keys(occurrences.taxonomyHierarchy.mappings).length} niveau(x)
                    </p>
                    <p className="text-xs">
                      Niveaux mappés : {Object.entries(occurrences.taxonomyHierarchy.mappings)
                        .map(([level, col]) => `${level} (${col})`)
                        .join(', ')}
                    </p>
                    <p className="mt-2">
                      La taxonomie complète sera extraite lors de l'import en respectant cette hiérarchie.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Bouton Suivant */}
          {hasTaxonomyMapping && (
            <div className="flex justify-end">
              <Button
                onClick={() => setActiveTab('enrichment')}
                className="gap-2"
              >
                Suivant : Enrichissement (optionnel)
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          )}
        </TabsContent>

        <TabsContent value="enrichment" className="space-y-4">
          <Alert className="border-blue-200 bg-blue-50 dark:bg-blue-900/20">
            <Globe className="w-4 h-4 text-blue-600" />
            <AlertTitle>Enrichissement via API externe</AlertTitle>
            <AlertDescription>
              Optionnel : Enrichissez votre taxonomie avec des données provenant d'APIs externes
              (statut de conservation, endémisme, images, etc.)
            </AlertDescription>
          </Alert>

          <ApiEnrichmentConfig
            config={apiConfig}
            onChange={handleApiConfigChange}
          />

          {/* Note informative */}
          <Alert>
            <Info className="w-4 h-4" />
            <AlertDescription>
              L'enrichissement API est optionnel. Vous pouvez passer à l'étape suivante
              (Agrégations spatiales) en utilisant le bouton "Suivant" en bas de la page principale.
            </AlertDescription>
          </Alert>
        </TabsContent>
      </Tabs>

      {/* Status summary */}
      <Card className={hasRequiredFields && hasTaxonomyMapping ? 'border-green-500' : ''}>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            État de configuration
            {hasRequiredFields && hasTaxonomyMapping && (
              <CheckCircle className="w-5 h-5 text-green-600" />
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              {occurrences.fieldMappings.taxon_id ? (
                <CheckCircle className="w-4 h-4 text-green-600" />
              ) : (
                <AlertCircle className="w-4 h-4 text-muted-foreground" />
              )}
              <span className="text-sm">Identifiant taxonomique mappé</span>
            </div>
            <div className="flex items-center gap-2">
              {occurrences.fieldMappings.location ? (
                <CheckCircle className="w-4 h-4 text-green-600" />
              ) : (
                <AlertCircle className="w-4 h-4 text-muted-foreground" />
              )}
              <span className="text-sm">Localisation mappée</span>
            </div>
            <div className="flex items-center gap-2">
              {hasTaxonomyMapping ? (
                <CheckCircle className="w-4 h-4 text-green-600" />
              ) : (
                <AlertCircle className="w-4 h-4 text-muted-foreground" />
              )}
              <span className="text-sm">
                Hiérarchie taxonomique configurée ({Object.keys(occurrences.taxonomyHierarchy.mappings).length} niveaux)
              </span>
            </div>
            {occurrences.fieldMappings.plot_name && (
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4 text-blue-600" />
                <span className="text-sm">Lien vers plots détecté</span>
              </div>
            )}
            {apiConfig.enabled && (
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-blue-600" />
                <span className="text-sm">Enrichissement API activé</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
