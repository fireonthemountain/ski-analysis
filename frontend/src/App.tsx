import { useState } from 'react'
import VideoUpload from './components/VideoUpload'
import AnalysisResults from './components/AnalysisResults'
import './App.css'

function App() {
  const [uploadedVideoId, setUploadedVideoId] = useState<string | null>(null)
  const [showResults, setShowResults] = useState(false)

  const handleUploadSuccess = (videoId: string) => {
    console.log('Video/Photo uploaded successfully:', videoId)
    setUploadedVideoId(videoId)
    // Show results immediately for photos
    setTimeout(() => setShowResults(true), 1000)
  }

  const handleBackToUpload = () => {
    setUploadedVideoId(null)
    setShowResults(false)
  }

  const handleUploadError = (error: string) => {
    console.error('Upload error:', error)
  }

  return (
    <>
      <div className="container">
        <header>
          <h1>🎿 Ski Technique Analysis</h1>
          <p className="subtitle">Analyze and improve your skiing technique with AI</p>
        </header>

        <main>
          {!uploadedVideoId ? (
            <>
              <section className="hero">
                <h2>Upload Your Skiing Photo</h2>
                <p>Get instant AI-powered feedback on your technique and form</p>
              </section>

              <VideoUpload
                onUploadSuccess={handleUploadSuccess}
                onUploadError={handleUploadError}
              />

              <section className="features">
                <div className="feature-card">
                  <h3>📸 Instant Analysis</h3>
                  <p>Upload a photo and get immediate technique feedback</p>
                </div>

                <div className="feature-card">
                  <h3>🤖 AI Insights</h3>
                  <p>Advanced pose detection and biomechanical evaluation</p>
                </div>

                <div className="feature-card">
                  <h3>💡 Coaching Tips</h3>
                  <p>Personalized recommendations to improve your skiing</p>
                </div>
              </section>
            </>
          ) : showResults ? (
            <AnalysisResults
              videoId={uploadedVideoId}
              onBack={handleBackToUpload}
            />
          ) : (
            <section className="processing">
              <div className="processing-card">
                <div className="processing-icon">⚙️</div>
                <h2>Analyzing Your Photo</h2>
                <p className="processing-message">
                  Detecting pose and analyzing technique...
                </p>
                <div className="processing-spinner"></div>
                <p className="video-id">ID: {uploadedVideoId}</p>
              </div>
            </section>
          )}

          <section className="status">
            <p className="status-badge">✅ Photo analysis is live! Upload a skiing photo to try it.</p>
          </section>
        </main>

        <footer>
          <p>Built with ⛷️ by skiers, for skiers</p>
        </footer>
      </div>
    </>
  )
}

export default App
