import React, { useRef, useState } from 'react'
import { api } from '../api/client'

const ACCEPTED_TYPES = '.pdf,.txt,.csv,.docx,.xlsx,.json,.png,.jpg,.jpeg,.webp'

/**
 * File upload component with drag-and-drop support.
 * Calls onUpload(filename, originalName) when upload succeeds.
 */
export default function FileUpload({ onUpload, onError }) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef(null)

  const handleFile = async (file) => {
    if (!file) return
    setUploading(true)
    try {
      const result = await api.uploadFile(file)
      onUpload(result.filename, result.original_name, result.mime_type)
    } catch (err) {
      onError(err.message)
    } finally {
      setUploading(false)
    }
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <>
      <input
        ref={fileRef}
        type="file"
        accept={ACCEPTED_TYPES}
        style={{ display: 'none' }}
        onChange={(e) => handleFile(e.target.files[0])}
        id="file-upload-input"
      />
      <button
        id="attach-file-btn"
        className="btn-icon"
        title="Attach file"
        disabled={uploading}
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={dragging ? { borderColor: 'var(--border-active)', background: 'rgba(124,58,237,0.1)' } : {}}
      >
        {uploading ? (
          <div className="step-spinner" style={{ width: 14, height: 14 }} />
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
          </svg>
        )}
      </button>
    </>
  )
}
