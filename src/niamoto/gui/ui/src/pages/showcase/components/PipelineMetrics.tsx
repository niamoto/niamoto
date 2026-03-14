import { Clock, Database, Zap, FileCheck, Target } from 'lucide-react';

interface PipelineMetricsProps {
  type: 'import' | 'transform' | 'export';
  result?: any;
  duration?: number;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}m ${secs}s`;
}

export function PipelineMetrics({ type, result, duration }: PipelineMetricsProps) {
  if (!result) return null;

  if (type === 'import') {
    // Extract import metrics from structured result
    const metrics = result.metrics || {};
    const taxonomy = metrics.taxonomy || 0;
    const occurrences = metrics.occurrences || 0;
    const plots = metrics.plots || 0;
    const shapes = metrics.shapes || 0;

    const total = taxonomy + occurrences + plots + shapes;

    return (
      <div className="space-y-3 text-sm">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Clock className="h-4 w-4" />
          <span>Durée: {duration ? formatDuration(duration) : '—'}</span>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-2 font-medium">
            <Database className="h-4 w-4 text-blue-500" />
            <span>Données importées</span>
          </div>
          <div className="ml-6 space-y-1 text-muted-foreground">
            {taxonomy > 0 && <div>• Taxonomie: {taxonomy.toLocaleString()} taxons</div>}
            {occurrences > 0 && <div>• Occurrences: {occurrences.toLocaleString()}</div>}
            {plots > 0 && <div>• Parcelles: {plots.toLocaleString()}</div>}
            {shapes > 0 && <div>• Formes: {shapes.toLocaleString()}</div>}
          </div>
        </div>

        <div className="flex items-center gap-2 text-green-500 font-medium">
          <FileCheck className="h-4 w-4" />
          <span>Succès: {total.toLocaleString()} enregistrements importés</span>
        </div>
      </div>
    );
  }

  if (type === 'transform') {
    // Extract transform metrics from result structure
    const groups: { [key: string]: { items: number; widgets: number } } = {};
    let totalWidgets = 0;

    // Check if we have the new API format with metrics and transformations
    const transformations = result.transformations || result;

    // Group transformations by group name
    Object.entries(transformations).forEach(([key, transData]: [string, any]) => {
      if (transData && typeof transData === 'object') {
        const groupName = transData.group || key;
        const generated = transData.generated || 0;

        if (!groups[groupName]) {
          groups[groupName] = { items: 0, widgets: 0 };
        }

        groups[groupName].items += 1; // Count number of transformations
        groups[groupName].widgets += generated;
        totalWidgets += generated;
      }
    });

    const totalItems = Object.values(groups).reduce((sum, g) => sum + g.items, 0);
    const itemsPerSecond = duration && totalItems > 0 ? (totalItems / duration).toFixed(1) : '0';

    return (
      <div className="space-y-3 text-sm">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Clock className="h-4 w-4" />
          <span>Durée: {duration ? formatDuration(duration) : '—'}</span>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-2 font-medium">
            <Database className="h-4 w-4 text-green-500" />
            <span>Groupes traités</span>
          </div>
          <div className="ml-6 space-y-1 text-muted-foreground">
            {Object.entries(groups).map(([name, data]) => (
              <div key={name}>
                • {name.charAt(0).toUpperCase() + name.slice(1)}: {data.items} éléments → {data.widgets} widgets générés
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex items-center gap-2 font-medium">
            <FileCheck className="h-4 w-4 text-green-500" />
            <span>Total: {totalWidgets.toLocaleString()} widgets générés</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground ml-6">
            <Zap className="h-4 w-4" />
            <span>Performance: {itemsPerSecond} éléments/seconde</span>
          </div>
        </div>
      </div>
    );
  }

  if (type === 'export') {
    // Extract export metrics
    const targets: { [key: string]: number } = {};
    let totalFiles = 0;

    // Parse exports from result
    if (result.exports) {
      Object.entries(result.exports).forEach(([name, exportData]: [string, any]) => {
        if (exportData) {
          let fileCount = 0;

          // Try to get files_generated from exportData.data (new format)
          if (exportData.data && typeof exportData.data === 'object') {
            fileCount = exportData.data.files_generated || 0;
          }

          // Fallback: try to count files from data structure
          if (fileCount === 0 && exportData.data && typeof exportData.data === 'object') {
            Object.values(exportData.data).forEach((value: any) => {
              if (Array.isArray(value)) {
                fileCount += value.length;
              } else if (value && typeof value === 'object' && value.files) {
                fileCount += value.files.length || 0;
              }
            });
          }

          if (fileCount > 0) {
            targets[name] = fileCount;
            totalFiles += fileCount;
          }
        }
      });
    }

    // Fallback: try to get from metrics
    const metrics = result.metrics;
    if (metrics && Object.keys(targets).length === 0) {
      totalFiles = metrics.generated_pages || 0;
    }

    const successRate = result.metrics?.completed_exports && result.metrics?.total_exports
      ? ((result.metrics.completed_exports / result.metrics.total_exports) * 100).toFixed(0)
      : '100';

    return (
      <div className="space-y-3 text-sm">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Clock className="h-4 w-4" />
          <span>Durée: {duration ? formatDuration(duration) : '—'}</span>
        </div>

        <div>
          <div className="flex items-center gap-2 mb-2 font-medium">
            <Target className="h-4 w-4 text-purple-500" />
            <span>Cibles</span>
          </div>
          <div className="ml-6 space-y-1 text-muted-foreground">
            {Object.entries(targets).map(([name, files]) => (
              <div key={name}>
                • {name}: {files.toLocaleString()} fichiers générés
              </div>
            ))}
            {Object.keys(targets).length === 0 && totalFiles > 0 && (
              <div>• Export: {totalFiles.toLocaleString()} fichiers générés</div>
            )}
          </div>
        </div>

        <div className="space-y-1">
          <div className="flex items-center gap-2 font-medium">
            <FileCheck className="h-4 w-4 text-green-500" />
            <span>Total: {totalFiles.toLocaleString()} fichiers générés</span>
          </div>
          <div className="flex items-center gap-2 text-green-500 ml-6">
            <Zap className="h-4 w-4" />
            <span>Taux de réussite: {successRate}% cibles complétées</span>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
