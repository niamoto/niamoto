import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Database, Table, Search, Filter, Download, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export function DataExplorer() {
  const { t } = useTranslation()
  const [selectedTable, setSelectedTable] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')

  // Mock data for demonstration
  const tables = [
    { name: 'occurrences', count: 15234, description: 'Species occurrence data' },
    { name: 'taxon', count: 2456, description: 'Taxonomic hierarchy' },
    { name: 'plots', count: 567, description: 'Plot locations and metadata' },
    { name: 'shapes', count: 89, description: 'Geographic boundaries' },
  ]

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
          <Button variant="outline" size="sm">
            <RefreshCw className="mr-2 h-4 w-4" />
            {t('common.refresh', 'Refresh')}
          </Button>
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            {t('common.export', 'Export')}
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
              {tables.map((table) => (
                <button
                  key={table.name}
                  onClick={() => setSelectedTable(table.name)}
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
              ))}
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
                      placeholder={t('data_explorer.search_placeholder', 'Search...')}
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="flex-1"
                    />
                    <Button>
                      <Search className="mr-2 h-4 w-4" />
                      {t('common.search', 'Search')}
                    </Button>
                    <Button variant="outline">
                      <Filter className="mr-2 h-4 w-4" />
                      {t('common.filter', 'Filter')}
                    </Button>
                  </div>

                  <div className="grid gap-2 md:grid-cols-3">
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder={t('data_explorer.select_column', 'Select column')} />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="id">ID</SelectItem>
                        <SelectItem value="name">Name</SelectItem>
                        <SelectItem value="date">Date</SelectItem>
                      </SelectContent>
                    </Select>
                    <Select>
                      <SelectTrigger>
                        <SelectValue placeholder={t('data_explorer.operator', 'Operator')} />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="equals">Equals</SelectItem>
                        <SelectItem value="contains">Contains</SelectItem>
                        <SelectItem value="greater">Greater than</SelectItem>
                        <SelectItem value="less">Less than</SelectItem>
                      </SelectContent>
                    </Select>
                    <Input placeholder={t('data_explorer.value', 'Value')} />
                  </div>
                </CardContent>
              </Card>

              {/* Results */}
              <Card>
                <CardHeader>
                  <CardTitle>{t('data_explorer.results', 'Results')}</CardTitle>
                  <CardDescription>
                    {t('data_explorer.showing_records', 'Showing {count} records', { count: 100 })}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Tabs defaultValue="table">
                    <TabsList>
                      <TabsTrigger value="table">{t('data_explorer.table_view', 'Table')}</TabsTrigger>
                      <TabsTrigger value="chart">{t('data_explorer.chart_view', 'Chart')}</TabsTrigger>
                      <TabsTrigger value="map">{t('data_explorer.map_view', 'Map')}</TabsTrigger>
                    </TabsList>
                    <TabsContent value="table" className="mt-4">
                      <div className="rounded-lg border p-4">
                        <p className="text-sm text-muted-foreground text-center py-8">
                          {t('data_explorer.table_preview', 'Table data will be displayed here')}
                        </p>
                      </div>
                    </TabsContent>
                    <TabsContent value="chart" className="mt-4">
                      <div className="rounded-lg border p-4">
                        <p className="text-sm text-muted-foreground text-center py-8">
                          {t('data_explorer.chart_preview', 'Chart visualization will be displayed here')}
                        </p>
                      </div>
                    </TabsContent>
                    <TabsContent value="map" className="mt-4">
                      <div className="rounded-lg border p-4">
                        <p className="text-sm text-muted-foreground text-center py-8">
                          {t('data_explorer.map_preview', 'Map visualization will be displayed here')}
                        </p>
                      </div>
                    </TabsContent>
                  </Tabs>
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
    </div>
  )
}
