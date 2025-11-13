/**
 * API client for file upload endpoints
 */

import { apiClient } from './client'

export interface UploadedFileInfo {
  filename: string
  path: string
  size: number
  size_mb: number
  type: string
  category: string
}

export interface UploadResponse {
  success: boolean
  uploaded_files: UploadedFileInfo[]
  uploaded_count: number
  existing_files: string[]  // List of filenames that already exist
  existing_count: number
  errors: string[]
}

/**
 * Upload multiple files to the imports directory
 *
 * @param files - Files to upload
 * @param overwrite - If true, overwrite existing files. If false, skip existing files.
 */
export async function uploadFiles(
  files: File[],
  overwrite: boolean = false
): Promise<UploadResponse> {
  const formData = new FormData()

  files.forEach(file => {
    formData.append('files', file)
  })

  const response = await apiClient.post<UploadResponse>(
    `/smart/upload-files?overwrite=${overwrite}`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 300000 // 5 minutes for large files
    }
  )

  return response.data
}
