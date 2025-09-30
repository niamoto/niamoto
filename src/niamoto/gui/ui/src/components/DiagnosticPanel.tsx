import { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, Database, FolderOpen, FileText } from 'lucide-react';

interface DiagnosticInfo {
  working_directory: string;
  database: {
    path: string | null;
    exists: boolean;
    tables: string[];
  };
  config_files: {
    [key: string]: {
      exists: boolean;
      path: string;
    };
  };
}

export function DiagnosticPanel() {
  const [diagnostic, setDiagnostic] = useState<DiagnosticInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/bootstrap/diagnostic')
      .then((res) => res.json())
      .then((data) => {
        setDiagnostic(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="rounded-lg border bg-card p-4">
        <p className="text-sm text-muted-foreground">Chargement des informations de diagnostic...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-destructive" />
          <p className="text-sm font-medium">Erreur de diagnostic</p>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">{error}</p>
      </div>
    );
  }

  if (!diagnostic) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Working Directory */}
      <div className="rounded-lg border bg-card p-4">
        <div className="flex items-center gap-2 mb-2">
          <FolderOpen className="h-5 w-5 text-primary" />
          <h3 className="font-medium">Répertoire de travail</h3>
        </div>
        <p className="text-sm text-muted-foreground font-mono">{diagnostic.working_directory}</p>
      </div>

      {/* Database */}
      <div className="rounded-lg border bg-card p-4">
        <div className="flex items-center gap-2 mb-2">
          <Database className="h-5 w-5 text-primary" />
          <h3 className="font-medium">Base de données</h3>
          {diagnostic.database.exists ? (
            <CheckCircle className="h-4 w-4 text-green-500 ml-auto" />
          ) : (
            <AlertCircle className="h-4 w-4 text-destructive ml-auto" />
          )}
        </div>
        <p className="text-sm text-muted-foreground font-mono mb-2">
          {diagnostic.database.path || 'Non trouvée'}
        </p>
        {diagnostic.database.exists && diagnostic.database.tables.length > 0 && (
          <div className="mt-2">
            <p className="text-xs text-muted-foreground mb-1">
              Tables ({diagnostic.database.tables.length}) :
            </p>
            <div className="flex flex-wrap gap-1">
              {diagnostic.database.tables.slice(0, 10).map((table) => (
                <span
                  key={table}
                  className="inline-flex items-center rounded-md bg-primary/10 px-2 py-1 text-xs font-medium text-primary"
                >
                  {table}
                </span>
              ))}
              {diagnostic.database.tables.length > 10 && (
                <span className="inline-flex items-center rounded-md bg-muted px-2 py-1 text-xs font-medium">
                  +{diagnostic.database.tables.length - 10} autres
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Config Files */}
      <div className="rounded-lg border bg-card p-4">
        <div className="flex items-center gap-2 mb-2">
          <FileText className="h-5 w-5 text-primary" />
          <h3 className="font-medium">Fichiers de configuration</h3>
        </div>
        <div className="space-y-2">
          {Object.entries(diagnostic.config_files).map(([filename, info]) => (
            <div key={filename} className="flex items-center justify-between">
              <span className="text-sm font-mono">{filename}</span>
              {info.exists ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : (
                <AlertCircle className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
