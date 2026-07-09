import { useEffect, useState } from 'react'
import './AnalysisResults.css'

interface Recommendation {
  category: string
  issue: string
  suggestion: string
  priority: string
}

interface Scores {
  overall_score: number
  stance_score?: number
  balance_score?: number
  lower_body_score?: number
  upper_body_score?: number
}

interface Metrics {
  forward_lean_angle: number
  avg_knee_flexion: number
  hip_ankle_alignment: number
  shoulder_alignment: number
  center_of_mass: {
    balance: number
  }
}

interface AnalysisData {
  id: string
  video_id: string
  created_at: string
  metrics: Metrics
  recommendations: Recommendation[]
  scores: Scores
  overall_score: number
  pose_data: any
}

interface VideoData {
  id: string
  storage_url: string
  original_filename: string
  processing_status: string
}

interface AnalysisResultsProps {
  videoId: string
  onBack?: () => void
}

export function AnalysisResults({ videoId, onBack }: AnalysisResultsProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null)
  const [video, setVideo] = useState<VideoData | null>(null)
  const [showSkeleton, setShowSkeleton] = useState(true)

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

  useEffect(() => {
    fetchAnalysis()
    fetchVideo()
  }, [videoId])

  const fetchAnalysis = async () => {
    try {
      const response = await fetch(`${API_URL}/analysis/${videoId}`)

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Analysis not yet available. Please wait...')
        }
        throw new Error('Failed to fetch analysis')
      }

      const data = await response.json()
      setAnalysis(data)
      setLoading(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analysis')
      setLoading(false)
    }
  }

  const fetchVideo = async () => {
    try {
      const response = await fetch(`${API_URL}/videos/${videoId}`)
      if (response.ok) {
        const data = await response.json()
        setVideo(data)
      }
    } catch (err) {
      console.error('Failed to fetch video:', err)
    }
  }

  const getScoreColor = (score: number): string => {
    if (score >= 80) return '#22c55e'
    if (score >= 60) return '#f59e0b'
    return '#ef4444'
  }

  const getPriorityColor = (priority: string): string => {
    if (priority === 'high') return '#ef4444'
    if (priority === 'medium') return '#f59e0b'
    return '#22c55e'
  }

  if (loading) {
    return (
      <div className="analysis-loading">
        <div className="spinner"></div>
        <p>Loading analysis results...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="analysis-error">
        <span className="error-icon">⚠️</span>
        <p>{error}</p>
        <button onClick={onBack} className="back-button">Go Back</button>
      </div>
    )
  }

  if (!analysis) {
    return null
  }

  return (
    <div className="analysis-container">
      <div className="analysis-header">
        <h2>🎿 Analysis Results</h2>
        {onBack && (
          <button onClick={onBack} className="back-button-small">
            ← Back
          </button>
        )}
      </div>

      {/* Photo Display */}
      {video && (
        <div className="photo-section">
          <div className="photo-controls">
            <button
              className={`view-toggle ${!showSkeleton ? 'active' : ''}`}
              onClick={() => setShowSkeleton(false)}
            >
              Original
            </button>
            <button
              className={`view-toggle ${showSkeleton ? 'active' : ''}`}
              onClick={() => setShowSkeleton(true)}
            >
              Skeleton Overlay
            </button>
          </div>
          <img
            src={showSkeleton ? `${API_URL}/analysis/${videoId}/skeleton` : video.storage_url}
            alt={video.original_filename}
            className="analyzed-photo"
          />
          <p className="photo-caption">
            {showSkeleton ? 'Detected pose landmarks shown in green' : video.original_filename}
          </p>
        </div>
      )}

      {/* Overall Score */}
      <div className="overall-score-card">
        <div className="score-circle" style={{ borderColor: getScoreColor(analysis.overall_score) }}>
          <span className="score-number">{Math.round(analysis.overall_score)}</span>
          <span className="score-label">/100</span>
        </div>
        <div className="score-description">
          <h3>Overall Technique Score</h3>
          <p>
            {analysis.overall_score >= 80 && '🌟 Excellent form! Keep it up!'}
            {analysis.overall_score >= 60 && analysis.overall_score < 80 && '👍 Good technique with room for improvement'}
            {analysis.overall_score < 60 && '💪 Focus on the recommendations below to improve'}
          </p>
        </div>
      </div>

      {/* Detailed Scores */}
      <div className="scores-grid">
        {analysis.scores.stance_score !== undefined && (
          <div className="score-card">
            <h4>Stance</h4>
            <div className="score-bar">
              <div
                className="score-fill"
                style={{
                  width: `${analysis.scores.stance_score}%`,
                  backgroundColor: getScoreColor(analysis.scores.stance_score)
                }}
              ></div>
            </div>
            <span className="score-value">{Math.round(analysis.scores.stance_score)}/100</span>
          </div>
        )}

        {analysis.scores.balance_score !== undefined && (
          <div className="score-card">
            <h4>Balance</h4>
            <div className="score-bar">
              <div
                className="score-fill"
                style={{
                  width: `${analysis.scores.balance_score}%`,
                  backgroundColor: getScoreColor(analysis.scores.balance_score)
                }}
              ></div>
            </div>
            <span className="score-value">{Math.round(analysis.scores.balance_score)}/100</span>
          </div>
        )}

        {analysis.scores.lower_body_score !== undefined && (
          <div className="score-card">
            <h4>Lower Body</h4>
            <div className="score-bar">
              <div
                className="score-fill"
                style={{
                  width: `${analysis.scores.lower_body_score}%`,
                  backgroundColor: getScoreColor(analysis.scores.lower_body_score)
                }}
              ></div>
            </div>
            <span className="score-value">{Math.round(analysis.scores.lower_body_score)}/100</span>
          </div>
        )}

        {analysis.scores.upper_body_score !== undefined && (
          <div className="score-card">
            <h4>Upper Body</h4>
            <div className="score-bar">
              <div
                className="score-fill"
                style={{
                  width: `${analysis.scores.upper_body_score}%`,
                  backgroundColor: getScoreColor(analysis.scores.upper_body_score)
                }}
              ></div>
            </div>
            <span className="score-value">{Math.round(analysis.scores.upper_body_score)}/100</span>
          </div>
        )}
      </div>

      {/* Key Metrics */}
      <div className="metrics-section">
        <h3>📊 Key Metrics</h3>
        <div className="metrics-grid">
          <div className="metric-item">
            <span className="metric-label">Forward Lean</span>
            <span className="metric-value">{Math.round(analysis.metrics.forward_lean_angle)}°</span>
            <span className="metric-ideal">Ideal: 15-25°</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Knee Flexion</span>
            <span className="metric-value">{Math.round(analysis.metrics.avg_knee_flexion)}°</span>
            <span className="metric-ideal">Ideal: 140-160°</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Balance</span>
            <span className="metric-value">{Math.round(analysis.metrics.center_of_mass.balance)}/100</span>
            <span className="metric-ideal">Higher is better</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Shoulder Level</span>
            <span className="metric-value">{Math.round(analysis.metrics.shoulder_alignment)}°</span>
            <span className="metric-ideal">Ideal: &lt;5°</span>
          </div>
        </div>
      </div>

      {/* Recommendations */}
      <div className="recommendations-section">
        <h3>💡 Coaching Recommendations</h3>
        <div className="recommendations-list">
          {analysis.recommendations.map((rec, index) => (
            <div key={index} className="recommendation-card">
              <div className="recommendation-header">
                <span className="recommendation-category">{rec.category}</span>
                <span
                  className="recommendation-priority"
                  style={{ backgroundColor: getPriorityColor(rec.priority) }}
                >
                  {rec.priority}
                </span>
              </div>
              <h4 className="recommendation-issue">{rec.issue}</h4>
              <p className="recommendation-suggestion">{rec.suggestion}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="action-buttons">
        <button onClick={onBack} className="primary-button">
          Analyze Another Photo
        </button>
      </div>
    </div>
  )
}

export default AnalysisResults
