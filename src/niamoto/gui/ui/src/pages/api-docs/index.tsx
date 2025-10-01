export function ApiDocs() {
  return (
    <div className="h-full w-full flex flex-col">
      <div className="p-6 border-b">
        <h1 className="text-2xl font-bold">API Documentation</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Documentation interactive de l'API Niamoto (FastAPI / Swagger)
        </p>
      </div>

      <div className="flex-1 w-full">
        <iframe
          src="/api/docs"
          className="w-full h-full border-0"
          title="API Documentation"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
        />
      </div>
    </div>
  )
}
