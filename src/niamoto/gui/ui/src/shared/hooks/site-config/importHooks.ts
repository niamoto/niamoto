import { useMutation } from '@tanstack/react-query'
import { importBibtex, importCsv } from './siteConfigApi'

export function useImportBibtex() {
  return useMutation({
    mutationFn: (file: File) => importBibtex(file),
  })
}

export function useImportCsv() {
  return useMutation({
    mutationFn: ({
      file,
      delimiter,
      hasHeader,
    }: {
      file: File
      delimiter?: string
      hasHeader?: boolean
    }) => importCsv(file, delimiter, hasHeader),
  })
}
