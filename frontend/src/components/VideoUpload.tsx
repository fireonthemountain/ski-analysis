import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import './VideoUpload.css'

interface VideoUploadProps {
  onUploadSuccess?: (videoId: string) => void
  onUploadError?: (error: string) => void
}

interface UploadResponse {
  video_id: string
  filename: string
  status: string
  message: string
}

export function VideoUpload({ onUploadSuccess, onUploadError }: VideoUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploadedVideo, setUploadedVideo] = useState<UploadResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

  const uploadVideo = async (file: File) => {
    setUploading(true)
    setProgress(0)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const xhr = new XMLHttpRequest()

      // Track upload progress
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percentComplete = (e.loaded / e.total) * 100
          setProgress(Math.round(percentComplete))
        }
      })

      // Handle completion
      xhr.addEventListener('load', () => {
        if (xhr.status === 201) {
          const response: UploadResponse = JSON.parse(xhr.responseText)
          setUploadedVideo(response)
          setUploading(false)
          onUploadSuccess?.(response.video_id)
        } else {
          const errorData = JSON.parse(xhr.responseText)
          const errorMsg = errorData.detail || 'Upload failed'
          setError(errorMsg)
          setUploading(false)
          onUploadError?.(errorMsg)
        }
      })

      // Handle errors
      xhr.addEventListener('error', () => {
        const errorMsg = 'Network error during upload'
        setError(errorMsg)
        setUploading(false)
        onUploadError?.(errorMsg)
      })

      xhr.open('POST', `${API_URL}/videos/upload`)
      xhr.send(formData)

    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Upload failed'
      setError(errorMsg)
      setUploading(false)
      onUploadError?.(errorMsg)
    }
  }

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0]

      // Check if image or video
      const isImage = file.type.startsWith('image/')
      const isVideo = file.type.startsWith('video/')

      // Validate file size (10MB for images, 500MB for videos)
      const maxSize = isImage ? 10 * 1024 * 1024 : 500 * 1024 * 1024
      if (file.size > maxSize) {
        const maxSizeText = isImage ? '10MB' : '500MB'
        setError(`File too large. Maximum size: ${maxSizeText}`)
        return
      }

      // Validate file type
      const allowedImageTypes = ['image/jpeg', 'image/jpg', 'image/png']
      const allowedVideoTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska']
      const allowedTypes = [...allowedImageTypes, ...allowedVideoTypes]

      if (!allowedTypes.includes(file.type)) {
        setError('Invalid file type. Allowed: JPG, PNG (images) or MP4, AVI, MOV, MKV (videos)')
        return
      }

      uploadVideo(file)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'video/mp4': ['.mp4'],
      'video/avi': ['.avi'],
      'video/quicktime': ['.mov'],
      'video/x-matroska': ['.mkv']
    },
    maxFiles: 1,
    disabled: uploading
  })

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  return (
    <div className="video-upload-container">
      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? 'active' : ''} ${uploading ? 'disabled' : ''}`}
      >
        <input {...getInputProps()} />

        {!uploading && !uploadedVideo && (
          <div className="dropzone-content">
            <div className="upload-icon">📹</div>
            {isDragActive ? (
              <p className="dropzone-text">Drop your photo or video here...</p>
            ) : (
              <>
                <p className="dropzone-text">
                  Drag & drop your skiing photo here
                </p>
                <p className="dropzone-subtext">
                  or click to select a file
                </p>
                <p className="dropzone-formats">
                  📸 Photos: JPG, PNG (max 10MB) - Instant analysis!<br />
                  🎥 Videos: MP4, AVI, MOV, MKV (max 500MB) - Coming soon
                </p>
              </>
            )}
          </div>
        )}

        {uploading && (
          <div className="upload-progress">
            <div className="spinner"></div>
            <p className="progress-text">Uploading video...</p>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <p className="progress-percentage">{progress}%</p>
          </div>
        )}

        {uploadedVideo && (
          <div className="upload-success">
            <div className="success-icon">✅</div>
            <h3>Upload Successful!</h3>
            <p className="success-message">{uploadedVideo.message}</p>
            <p className="video-filename">{uploadedVideo.filename}</p>
            <button
              className="upload-another-btn"
              onClick={(e) => {
                e.stopPropagation()
                setUploadedVideo(null)
                setProgress(0)
              }}
            >
              Upload Another Video
            </button>
          </div>
        )}
      </div>

      {error && (
        <div className="error-message">
          <span className="error-icon">⚠️</span>
          <span>{error}</span>
          <button
            className="error-dismiss"
            onClick={() => setError(null)}
          >
            ×
          </button>
        </div>
      )}
    </div>
  )
}

export default VideoUpload
