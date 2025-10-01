import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Database, Table, Search, RefreshCw, Loader2, AlertCircle, Sparkles, FileCode, Globe, Package, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { getTables, queryTable, previewEnrichment, type TableInfo, type QueryResponse, type EnrichmentPreviewResponse } from '@/lib/api/data'
import { listExports, readExportFile, type ExportsListResponse, type ExportFileContent } from '@/lib/api/exports'
import { toast } from 'sonner'
import Editor from '@monaco-editor/react'

export function DataExplorer() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [selectedTable, setSelectedTable] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [tables, setTables] = useState<TableInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null)
  const [querying, setQuerying] = useState(false)
  const [currentPage, setCurrentPage] = useState(0)
  const pageSize = 100
  const [enrichmentModal, setEnrichmentModal] = useState(false)
  const [enrichmentData, setEnrichmentData] = useState<EnrichmentPreviewResponse | null>(null)
  const [enrichmentLoading, setEnrichmentLoading] = useState(false)

  // Exports state
  const [exports, setExports] = useState<ExportsListResponse | null>(null)
  const [exportsLoading, setExportsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<string>('database')

  // JSON viewer state
  const [jsonViewerModal, setJsonViewerModal] = useState(false)
  const [selectedJsonFile, setSelectedJsonFile] = useState<ExportFileContent | null>(null)
  const [jsonFileLoading, setJsonFileLoading] = useState(false)

  // Load tables on mount
  useEffect(() => {
    loadTables()
  }, [])

  // Load exports when tab changes
  useEffect(() => {
    if (activeTab === 'exports') {
      loadExports()
    }
  }, [activeTab])

  const loadExports = async () => {
    setExportsLoading(true)
    try {
      const data = await listExports()
      setExports(data)
    } catch (error) {
      console.error('Failed to load exports:', error)
      toast.error('Erreur lors du chargement des exports')
    } finally {
      setExportsLoading(false)
    }
  }

  const handleJsonFileClick = async (filePath: string) => {
    setJsonFileLoading(true)
    setJsonViewerModal(true)
    setSelectedJsonFile(null)

    try {
      const fileContent = await readExportFile(filePath)
      setSelectedJsonFile(fileContent)
    } catch (error) {
      console.error('Failed to load JSON file:', error)
      toast.error('Erreur lors du chargement du fichier')
      setJsonViewerModal(false)
    } finally {
      setJsonFileLoading(false)
    }
  }

  // Load query results when table changes
  useEffect(() => {
    if (selectedTable) {
      loadTableData()
    }
  }, [selectedTable, currentPage])

  const loadTables = async () => {
    setLoading(true)
    try {
      const data = await getTables()
      setTables(data)
    } catch (error) {
      console.error('Failed to load tables:', error)
      toast.error('Erreur lors du chargement des tables')
    } finally {
      setLoading(false)
    }
  }

  const loadTableData = async () => {
    if (!selectedTable) return

    setQuerying(true)
    try {
      const result = await queryTable({
        table: selectedTable,
        limit: pageSize,
        offset: currentPage * pageSize,
        where: searchQuery || undefined
      })
      setQueryResult(result)
    } catch (error) {
      console.error('Failed to query table:', error)
      toast.error('Erreur lors de la requête')
    } finally {
      setQuerying(false)
    }
  }

  const handleSearch = () => {
    setCurrentPage(0)
    loadTableData()
  }

  const handleTableSelect = (tableName: string) => {
    setSelectedTable(tableName)
    setSearchQuery('')
    setCurrentPage(0)
    setQueryResult(null)
  }

  const handleEnrichmentPreview = async (taxonName: string) => {
    setEnrichmentLoading(true)
    setEnrichmentModal(true)
    setEnrichmentData(null)

    try {
      const result = await previewEnrichment({ taxon_name: taxonName, table: selectedTable })
      setEnrichmentData(result)
    } catch (error) {
      console.error('Failed to preview enrichment:', error)
      toast.error('Erreur lors de la prévisualisation de l\'enrichissement')
      setEnrichmentModal(false)
    } finally {
      setEnrichmentLoading(false)
    }
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            {t('data_explorer.title', 'Data Explorer')}
          </h1>
          <p className="text-muted-foreground">
            {t('data_explorer.description', 'Browse and query your ecological data')}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={loadTables} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            {t('common.refresh', 'Actualiser')}
          </Button>
        </div>
      </div>

      {/* Tabs for Database and Exports */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="database" className="gap-2">
            <Database className="h-4 w-4" />
            Database
          </TabsTrigger>
          <TabsTrigger value="exports" className="gap-2">
            <Package className="h-4 w-4" />
            Exports
          </TabsTrigger>
        </TabsList>

        {/* Database Tab */}
        <TabsContent value="database" className="space-y-6">
      <div className="grid gap-6 md:grid-cols-3">
        {/* Sidebar - Table List */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                {t('data_explorer.tables', 'Tables')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : tables.length === 0 ? (
                <div className="text-center py-8">
                  <AlertCircle className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">
                    {t('data_explorer.no_tables', 'Aucune table disponible')}
                  </p>
                </div>
              ) : (
                tables.map((table) => (
                  <button
                    key={table.name}
                    onClick={() => handleTableSelect(table.name)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      selectedTable === table.name
                        ? 'bg-accent border-accent-foreground/20'
                        : 'hover:bg-muted border-transparent'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Table className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium">{table.name}</span>
                      </div>
                      <span className="text-sm text-muted-foreground">
                        {table.count.toLocaleString()}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {table.description}
                    </p>
                  </button>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        {/* Main Content Area */}
        <div className="md:col-span-2 space-y-4">
          {selectedTable ? (
            <>
              {/* Query Builder */}
              <Card>
                <CardHeader>
                  <CardTitle>{t('data_explorer.query_builder', 'Query Builder')}</CardTitle>
                  <CardDescription>
                    {t('data_explorer.query_description', 'Build queries to filter and analyze data')}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex gap-2">
                    <Input
                      placeholder={t('data_explorer.search_placeholder', 'WHERE clause (ex: id > 100)')}
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                      className="flex-1"
                    />
                    <Button onClick={handleSearch} disabled={querying}>
                      {querying ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Search className="mr-2 h-4 w-4" />
                      )}
                      {t('common.search', 'Rechercher')}
                    </Button>
                  </div>

                  <div className="text-xs text-muted-foreground">
                    <p>Exemples de requêtes WHERE :</p>
                    <ul className="list-disc list-inside mt-1 space-y-0.5">
                      <li><code className="bg-muted px-1 rounded">id &lt; 100</code></li>
                      <li><code className="bg-muted px-1 rounded">full_name LIKE '%Araucaria%'</code></li>
                      <li><code className="bg-muted px-1 rounded">dbh &gt; 50 AND height &lt; 30</code></li>
                    </ul>
                  </div>
                </CardContent>
              </Card>

              {/* Results */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>{t('data_explorer.results', 'Résultats')}</CardTitle>
                      <CardDescription>
                        {queryResult
                          ? `Affichage de ${queryResult.page_count} sur ${queryResult.total_count.toLocaleString()} enregistrements`
                          : t('data_explorer.no_query', 'Exécutez une requête pour voir les résultats')}
                      </CardDescription>
                    </div>
                    {queryResult && queryResult.total_count > pageSize && (
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setCurrentPage(Math.max(0, currentPage - 1))}
                          disabled={currentPage === 0 || querying}
                        >
                          Précédent
                        </Button>
                        <span className="text-sm text-muted-foreground">
                          Page {currentPage + 1} / {Math.ceil(queryResult.total_count / pageSize)}
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setCurrentPage(currentPage + 1)}
                          disabled={currentPage >= Math.floor(queryResult.total_count / pageSize) || querying}
                        >
                          Suivant
                        </Button>
                      </div>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  {querying ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                  ) : queryResult && queryResult.rows.length > 0 ? (
                    <div className="rounded-lg border overflow-auto max-h-[600px]">
                      <table className="w-full text-sm">
                        <thead className="bg-muted/50 sticky top-0">
                          <tr>
                            {selectedTable === 'taxon_ref' && <th className="px-4 py-2 text-left font-medium whitespace-nowrap">Actions</th>}
                            {queryResult.columns.map((col) => (
                              <th key={col} className="px-4 py-2 text-left font-medium whitespace-nowrap">
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {queryResult.rows.map((row, idx) => (
                            <tr key={idx} className="border-t hover:bg-muted/30">
                              {selectedTable === 'taxon_ref' && (
                                <td className="px-4 py-2 whitespace-nowrap">
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => handleEnrichmentPreview(row['full_name'])}
                                    disabled={!row['full_name']}
                                    className="h-8 px-2"
                                  >
                                    <Sparkles className="h-4 w-4" />
                                  </Button>
                                </td>
                              )}
                              {queryResult.columns.map((col) => (
                                <td key={col} className="px-4 py-2 whitespace-nowrap">
                                  {row[col] !== null && row[col] !== undefined
                                    ? String(row[col]).length > 100
                                      ? String(row[col]).substring(0, 100) + '...'
                                      : String(row[col])
                                    : <span className="text-muted-foreground italic">null</span>
                                  }
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="rounded-lg border p-4">
                      <p className="text-sm text-muted-foreground text-center py-8">
                        {queryResult?.rows.length === 0
                          ? t('data_explorer.no_results', 'Aucun résultat trouvé')
                          : t('data_explorer.table_preview', 'Sélectionnez une table et cliquez sur Rechercher')}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Database className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-lg font-medium">
                  {t('data_explorer.select_table', 'Select a table to explore')}
                </p>
                <p className="text-sm text-muted-foreground mt-1">
                  {t('data_explorer.select_table_description', 'Choose a table from the list to start exploring your data')}
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
        </TabsContent>

        {/* Exports Tab */}
        <TabsContent value="exports" className="space-y-6">
          <div className="space-y-4">
            {exportsLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : !exports?.exists ? (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Package className="h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-lg font-medium">Aucun export disponible</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Exécutez le pipeline pour générer des exports
                  </p>
                </CardContent>
              </Card>
            ) : (
              <>
                {/* Export Statistics */}
                <div className="grid gap-4 md:grid-cols-3">
                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-2xl font-bold">{exports.web.length}</p>
                          <p className="text-xs text-muted-foreground">Pages HTML</p>
                        </div>
                        <Globe className="h-8 w-8 text-purple-500" />
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-2xl font-bold">{exports.api.length}</p>
                          <p className="text-xs text-muted-foreground">Fichiers JSON</p>
                        </div>
                        <FileCode className="h-8 w-8 text-blue-500" />
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-2xl font-bold">{exports.dwc.length}</p>
                          <p className="text-xs text-muted-foreground">Darwin Core</p>
                        </div>
                        <Database className="h-8 w-8 text-green-500" />
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Export Path */}
                {exports.path && (
                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-sm">
                          <Package className="h-4 w-4 text-muted-foreground" />
                          <span className="text-muted-foreground">Répertoire :</span>
                          <code className="px-2 py-1 bg-muted rounded font-mono text-xs">
                            {exports.path}
                          </code>
                        </div>
                        <Button variant="outline" size="sm" onClick={() => navigate('/data/preview')}>
                          <ExternalLink className="h-4 w-4 mr-2" />
                          Voir le site
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Web Exports */}
                {exports.web.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Globe className="h-5 w-5 text-purple-500" />
                        Pages Web ({exports.web.length})
                      </CardTitle>
                      <CardDescription>
                        Pages HTML statiques générées
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="rounded-lg border overflow-auto max-h-96">
                        <table className="w-full text-sm">
                          <thead className="bg-muted/50 sticky top-0">
                            <tr>
                              <th className="px-4 py-2 text-left font-medium">Fichier</th>
                              <th className="px-4 py-2 text-left font-medium">Chemin</th>
                              <th className="px-4 py-2 text-right font-medium">Taille</th>
                            </tr>
                          </thead>
                          <tbody>
                            {exports.web.slice(0, 50).map((file, idx) => (
                              <tr key={idx} className="border-t hover:bg-muted/30">
                                <td className="px-4 py-2 font-mono text-xs">{file.name}</td>
                                <td className="px-4 py-2 text-xs text-muted-foreground">{file.path}</td>
                                <td className="px-4 py-2 text-right text-xs">
                                  {(file.size / 1024).toFixed(1)} KB
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {exports.web.length > 50 && (
                          <div className="p-3 text-center text-sm text-muted-foreground border-t">
                            ... et {exports.web.length - 50} autres fichiers
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* API Exports */}
                {exports.api.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <FileCode className="h-5 w-5 text-blue-500" />
                        API JSON ({exports.api.length})
                      </CardTitle>
                      <CardDescription>
                        Fichiers JSON pour API statique
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="rounded-lg border overflow-auto max-h-96">
                        <table className="w-full text-sm">
                          <thead className="bg-muted/50 sticky top-0">
                            <tr>
                              <th className="px-4 py-2 text-left font-medium">Fichier</th>
                              <th className="px-4 py-2 text-left font-medium">Chemin</th>
                              <th className="px-4 py-2 text-right font-medium">Taille</th>
                            </tr>
                          </thead>
                          <tbody>
                            {exports.api.slice(0, 50).map((file, idx) => (
                              <tr
                                key={idx}
                                className="border-t hover:bg-muted/30 cursor-pointer"
                                onClick={() => handleJsonFileClick(file.path)}
                              >
                                <td className="px-4 py-2 font-mono text-xs">{file.name}</td>
                                <td className="px-4 py-2 text-xs text-muted-foreground">{file.path}</td>
                                <td className="px-4 py-2 text-right text-xs">
                                  {(file.size / 1024).toFixed(1)} KB
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {exports.api.length > 50 && (
                          <div className="p-3 text-center text-sm text-muted-foreground border-t">
                            ... et {exports.api.length - 50} autres fichiers
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Darwin Core Exports */}
                {exports.dwc.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Database className="h-5 w-5 text-green-500" />
                        Darwin Core ({exports.dwc.length})
                      </CardTitle>
                      <CardDescription>
                        Exports au format Darwin Core
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="rounded-lg border overflow-auto max-h-96">
                        <table className="w-full text-sm">
                          <thead className="bg-muted/50 sticky top-0">
                            <tr>
                              <th className="px-4 py-2 text-left font-medium">Fichier</th>
                              <th className="px-4 py-2 text-left font-medium">Chemin</th>
                              <th className="px-4 py-2 text-right font-medium">Taille</th>
                            </tr>
                          </thead>
                          <tbody>
                            {exports.dwc.slice(0, 50).map((file, idx) => (
                              <tr
                                key={idx}
                                className="border-t hover:bg-muted/30 cursor-pointer"
                                onClick={() => handleJsonFileClick(file.path)}
                              >
                                <td className="px-4 py-2 font-mono text-xs">{file.name}</td>
                                <td className="px-4 py-2 text-xs text-muted-foreground">{file.path}</td>
                                <td className="px-4 py-2 text-right text-xs">
                                  {(file.size / 1024).toFixed(1)} KB
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {exports.dwc.length > 50 && (
                          <div className="p-3 text-center text-sm text-muted-foreground border-t">
                            ... et {exports.dwc.length - 50} autres fichiers
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Enrichment Preview Modal */}
      <Dialog open={enrichmentModal} onOpenChange={setEnrichmentModal}>
        <DialogContent className="!max-w-7xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              {t('data_explorer.enrichment_preview', 'API Enrichment Preview')}
            </DialogTitle>
            <DialogDescription>
              {enrichmentData?.taxon_name && `Données enrichies pour : ${enrichmentData.taxon_name}`}
            </DialogDescription>
          </DialogHeader>

          {enrichmentLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : enrichmentData ? (
            <div className="space-y-4">
              {/* Config Info */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Configuration</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div>
                    <span className="font-medium">API URL:</span>{' '}
                    <span className="text-muted-foreground">{enrichmentData.config_used.api_url}</span>
                  </div>
                  <div>
                    <span className="font-medium">Query Field:</span>{' '}
                    <span className="text-muted-foreground">{enrichmentData.config_used.query_field}</span>
                  </div>
                </CardContent>
              </Card>

              {/* Images */}
              {enrichmentData.api_enrichment.images && Array.isArray(enrichmentData.api_enrichment.images) && enrichmentData.api_enrichment.images.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Images</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                      {enrichmentData.api_enrichment.images.slice(0, 6).map((img: any, idx: number) => (
                        <div key={idx} className="space-y-2">
                          <img
                            src={img.big_thumb || img.small_thumb}
                            alt={img.auteur || 'Image'}
                            className="w-full h-40 object-cover rounded-lg border"
                          />
                          {img.auteur && (
                            <p className="text-xs text-muted-foreground">© {img.auteur}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Single image fields */}
              {(enrichmentData.api_enrichment.image_big_thumb || enrichmentData.api_enrichment.image_small_thumb) && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Image</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <img
                        src={enrichmentData.api_enrichment.image_big_thumb || enrichmentData.api_enrichment.image_small_thumb}
                        alt="Taxon"
                        className="w-full max-w-md h-64 object-cover rounded-lg border"
                      />
                      {enrichmentData.api_enrichment.image_auteur && (
                        <p className="text-sm text-muted-foreground">© {enrichmentData.api_enrichment.image_auteur}</p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Other Data */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">Données enrichies</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="rounded-lg border">
                    <table className="w-full text-sm">
                      <thead className="bg-muted/50">
                        <tr>
                          <th className="px-4 py-2 text-left font-medium">Champ</th>
                          <th className="px-4 py-2 text-left font-medium">Valeur</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(enrichmentData.api_enrichment).map(([key, value]) => {
                          // Skip image fields already displayed
                          if (key === 'images' || key.startsWith('image_')) return null

                          return (
                            <tr key={key} className="border-t">
                              <td className="px-4 py-2 font-medium">{key}</td>
                              <td className="px-4 py-2">
                                {value !== null && value !== undefined ? (
                                  typeof value === 'object' ? (
                                    <pre className="text-xs overflow-auto max-h-32 bg-muted p-2 rounded">
                                      {JSON.stringify(value, null, 2)}
                                    </pre>
                                  ) : (
                                    String(value)
                                  )
                                ) : (
                                  <span className="text-muted-foreground italic">null</span>
                                )}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              Aucune donnée disponible
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* JSON Viewer Modal */}
      <Dialog open={jsonViewerModal} onOpenChange={setJsonViewerModal}>
        <DialogContent className="!max-w-7xl max-h-[90vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileCode className="h-5 w-5" />
              Visualisation JSON
            </DialogTitle>
            <DialogDescription>
              {selectedJsonFile?.path}
            </DialogDescription>
          </DialogHeader>

          {jsonFileLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : selectedJsonFile ? (
            <div className="flex-1 min-h-0">
              <div className="h-[600px] border rounded-lg overflow-hidden">
                <Editor
                  height="100%"
                  language="json"
                  value={selectedJsonFile.content}
                  theme="vs-dark"
                  options={{
                    readOnly: true,
                    minimap: { enabled: true },
                    scrollBeyondLastLine: false,
                    wordWrap: 'on',
                    automaticLayout: true,
                  }}
                />
              </div>
              <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
                <span>Taille : {(selectedJsonFile.size / 1024).toFixed(1)} KB</span>
                {selectedJsonFile.error && (
                  <span className="text-destructive">{selectedJsonFile.error}</span>
                )}
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              Aucun fichier sélectionné
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
