import { useState, useCallback } from 'react'
import { uploadDocument, getDocument } from '../services/api'
import type { DocumentType, UploadState } from '../types/document'

const INITIAL_STATE: UploadState = {
  stage: 'idle',
  progress: 0,
}

/**
 * useUpload — manages the full upload → extract → complete lifecycle.
 *
 * Stages:
 *   idle → uploading (HTTP POST progress) → extracting (polling status) → completed | failed
 */
export function useUpload() {
  const [state, setState] = useState<UploadState>(INITIAL_STATE)

  const reset = useCallback(() => {
    setState(INITIAL_STATE)
  }, [])

  const upload = useCallback(
    async (file: File, documentType: DocumentType) => {
      setState({ stage: 'uploading', progress: 0 })

      try {
        // ── Phase 1: HTTP upload ──────────────────────────────────────────
        const response = await uploadDocument(file, documentType, (percent) => {
          setState((s) => ({ ...s, progress: Math.min(percent, 90) }))
        })

        setState({
          stage: 'extracting',
          progress: 90,
          documentId: response.document_id,
          filename: response.filename,
        })

        // ── Phase 2: Poll for ANALYZED | FAILED ──────────────────────────
        const MAX_POLLS = 30
        const POLL_INTERVAL_MS = 2000

        for (let i = 0; i < MAX_POLLS; i++) {
          await delay(POLL_INTERVAL_MS)
          const doc = await getDocument(response.document_id)

          if (doc.status === 'ANALYZED') {
            setState({
              stage: 'completed',
              progress: 100,
              documentId: doc.id,
              filename: doc.filename,
            })
            return doc.id
          }

          if (doc.status === 'FAILED') {
            setState({
              stage: 'failed',
              progress: 0,
              error: 'Document processing failed. Please try again.',
            })
            return null
          }

          // Still PROCESSING — update progress bar slightly
          setState((s) => ({
            ...s,
            progress: Math.min(90 + Math.floor(((i + 1) / MAX_POLLS) * 10), 99),
          }))
        }

        // Timed out
        setState({
          stage: 'failed',
          progress: 0,
          error: 'Processing timed out. Your file may still be processing; check back later.',
        })
        return null
      } catch (err: unknown) {
        const message =
          err instanceof Error
            ? err.message
            : 'An unexpected error occurred. Please try again.'

        // Axios provides server error details
        const axiosMsg = (err as { response?: { data?: { detail?: string } } })
          ?.response?.data?.detail

        setState({
          stage: 'failed',
          progress: 0,
          error: axiosMsg ?? message,
        })
        return null
      }
    },
    []
  )

  return { state, upload, reset }
}

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
