/**
 * File validation utilities.
 * All validation runs client-side first; backend validates again as the source of truth.
 */

export const ALLOWED_EXTENSIONS = ['.pdf', '.txt'] as const
export const ALLOWED_MIME_TYPES = ['application/pdf', 'text/plain'] as const
export const MAX_FILE_SIZE_MB = 25
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

export interface ValidationResult {
  valid: boolean
  error?: string
}

/**
 * Returns the file extension in lowercase, e.g. ".pdf"
 */
export function getFileExtension(filename: string): string {
  const idx = filename.lastIndexOf('.')
  if (idx === -1) return ''
  return filename.slice(idx).toLowerCase()
}

/**
 * Validates extension, MIME type, and size.
 */
export function validateFile(file: File): ValidationResult {
  const ext = getFileExtension(file.name)

  if (!ALLOWED_EXTENSIONS.includes(ext as typeof ALLOWED_EXTENSIONS[number])) {
    return {
      valid: false,
      error: `Unsupported file type "${ext || '(none)'}". Please upload a PDF or TXT file.`,
    }
  }

  if (!ALLOWED_MIME_TYPES.includes(file.type as typeof ALLOWED_MIME_TYPES[number])) {
    // MIME type can be empty on some systems for .txt; allow that edge case
    if (!(ext === '.txt' && file.type === '')) {
      return {
        valid: false,
        error: `File MIME type "${file.type}" is not accepted. Expected PDF or plain text.`,
      }
    }
  }

  if (file.size === 0) {
    return { valid: false, error: 'File is empty. Please upload a non-empty document.' }
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      valid: false,
      error: `File is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum size is ${MAX_FILE_SIZE_MB} MB.`,
    }
  }

  return { valid: true }
}

/**
 * Human-readable file size string.
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
