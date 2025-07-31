import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useImport } from './ImportContext'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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
  const { t } = useTranslation(['import', 'common'])
  const { state, updateOccurrences } = useImport()
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
      response_mapping: {},
      include_images: true,
      include_synonyms: true,
      include_distributions: true,
      include_references: true
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
    // For tropicos_enricher, ensure we have the correct structure
    if (config.plugin === 'tropicos_enricher') {
      const tropicosConfig = {
        enabled: config.enabled,
        plugin: 'tropicos_enricher',
        api_key: config.api_key,
        query_field: config.query_field || 'full_name',
        rate_limit: config.rate_limit || 1.0,
        cache_results: config.cache_results !== false,
        include_images: config.include_images !== false,
        include_synonyms: config.include_synonyms !== false,
        include_distributions: config.include_distributions !== false,
        include_references: config.include_references !== false
      }
      updateOccurrences({ apiEnrichment: tropicosConfig as any })
    } else {
      updateOccurrences({ apiEnrichment: config as any })
    }
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
          {t('occurrences.title')}
        </h2>
        <p className="text-muted-foreground mt-2">
          {t('occurrences.description')}
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="upload" className="gap-2">
            {t('occurrences.steps.file')}
            {occurrences.file && <CheckCircle className="w-4 h-4" />}
          </TabsTrigger>
          <TabsTrigger value="mapping" disabled={!occurrences.file} className="gap-2">
            {t('occurrences.steps.requiredFields')}
            {hasRequiredFields && <CheckCircle className="w-4 h-4" />}
          </TabsTrigger>
          <TabsTrigger value="taxonomy" disabled={!hasRequiredFields} className="gap-2">
            {t('occurrences.steps.taxonomy')}
            {hasTaxonomyMapping && <CheckCircle className="w-4 h-4" />}
          </TabsTrigger>
          <TabsTrigger value="enrichment" disabled={!hasTaxonomyMapping} className="gap-2">
            {t('occurrences.steps.enrichment')}
            {apiConfig.enabled && <CheckCircle className="w-4 h-4" />}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upload" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('occurrences.file.title')}</CardTitle>
              <CardDescription>
                {t('occurrences.file.description')}
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
                    <AlertTitle>{t('common:file.analysisComplete')}</AlertTitle>
                    <AlertDescription>
                      <div className="mt-2 space-y-1">
                        <div>• {t('occurrences.file.detected', { rows: occurrences.fileAnalysis.rowCount || occurrences.fileAnalysis.row_count || occurrences.fileAnalysis.total_rows || 'N/A' })}</div>
                        <div>• {t('occurrences.file.foundColumns', { count: occurrences.fileAnalysis.columns?.length })}</div>
                        <div>• {t('common:file.encoding')} : {occurrences.fileAnalysis.encoding || 'UTF-8'}</div>
                      </div>
                    </AlertDescription>
                  </Alert>

                  {occurrences.fileAnalysis.preview && (
                    <div>
                      <h4 className="font-medium mb-2">{t('common:file.preview')}</h4>
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
                {t('occurrences.file.nextStep')}
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          )}
        </TabsContent>

        <TabsContent value="mapping" className="space-y-4">
          <Alert>
            <Info className="w-4 h-4" />
            <AlertDescription>
              {t('occurrences.requiredFields.note')}
            </AlertDescription>
          </Alert>

          <Card>
            <CardHeader>
              <CardTitle>{t('occurrences.requiredFields.title')}</CardTitle>
              <CardDescription>
                {t('occurrences.requiredFields.description')}
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
                {t('occurrences.requiredFields.nextStep')}
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          )}
        </TabsContent>

        <TabsContent value="taxonomy" className="space-y-4">
          <Alert className="border-green-200 bg-green-50 dark:bg-green-900/20">
            <TreePine className="w-4 h-4 text-green-600" />
            <AlertTitle>{t('occurrences.taxonomy.title')}</AlertTitle>
            <AlertDescription>
              {t('occurrences.taxonomy.description')}
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
                <CardTitle className="text-base">{t('occurrences.taxonomy.preview')}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="text-sm text-muted-foreground space-y-1">
                    <p>
                      {t('occurrences.taxonomy.configuredHierarchy', { count: Object.keys(occurrences.taxonomyHierarchy.mappings).length })}
                    </p>
                    <p className="text-xs">
                      {t('occurrences.taxonomy.mappedLevels', {
                        levels: Object.entries(occurrences.taxonomyHierarchy.mappings)
                          .map(([level, col]) => `${level} (${col})`)
                          .join(', ')
                      })}
                    </p>
                    <p className="mt-2">
                      {t('occurrences.taxonomy.extractionNote')}
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
                {t('occurrences.taxonomy.nextStep')}
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          )}
        </TabsContent>

        <TabsContent value="enrichment" className="space-y-4">
          <Alert className="border-blue-200 bg-blue-50 dark:bg-blue-900/20">
            <Globe className="w-4 h-4 text-blue-600" />
            <AlertTitle>{t('occurrences.enrichment.title')}</AlertTitle>
            <AlertDescription>
              {t('occurrences.enrichment.description')}
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
              {t('occurrences.enrichment.note')}
            </AlertDescription>
          </Alert>
        </TabsContent>
      </Tabs>

      {/* Status summary */}
      <Card className={hasRequiredFields && hasTaxonomyMapping ? 'border-green-500' : ''}>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            {t('occurrences.status.configurationStatus', { defaultValue: 'État de configuration' })}
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
              <span className="text-sm">{t('occurrences.status.taxIdMapped')}</span>
            </div>
            <div className="flex items-center gap-2">
              {occurrences.fieldMappings.location ? (
                <CheckCircle className="w-4 h-4 text-green-600" />
              ) : (
                <AlertCircle className="w-4 h-4 text-muted-foreground" />
              )}
              <span className="text-sm">{t('occurrences.status.locationMapped')}</span>
            </div>
            <div className="flex items-center gap-2">
              {hasTaxonomyMapping ? (
                <CheckCircle className="w-4 h-4 text-green-600" />
              ) : (
                <AlertCircle className="w-4 h-4 text-muted-foreground" />
              )}
              <span className="text-sm">
                {t('occurrences.status.hierarchyConfigured', { count: Object.keys(occurrences.taxonomyHierarchy.mappings).length })}
              </span>
            </div>
            {occurrences.fieldMappings.plot_name && (
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4 text-blue-600" />
                <span className="text-sm">{t('occurrences.status.plotLinkDetected')}</span>
              </div>
            )}
            {apiConfig.enabled && (
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-blue-600" />
                <span className="text-sm">{t('occurrences.status.apiEnrichmentEnabled')}</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
