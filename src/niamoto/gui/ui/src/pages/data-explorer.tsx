import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Database, Table, Search, RefreshCw, Loader2, AlertCircle, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { getTables, queryTable, previewEnrichment, type TableInfo, type QueryResponse, type EnrichmentPreviewResponse } from '@/lib/api/data'
import { toast } from 'sonner'

export function DataExplorer() {
  const { t } = useTranslation()
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

  // Load tables on mount
  useEffect(() => {
    loadTables()
  }, [])

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

      {/* Main Content */}
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
    </div>
  )
}
