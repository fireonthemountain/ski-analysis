# System Architecture

## Overview

The Ski Technique Analysis system is built using a modern microservices architecture with separate frontend, backend, and ML processing components.

## High-Level Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│                 │         │                  │         │                 │
│  Web Frontend   │────────▶│   API Gateway    │────────▶│  Video Storage  │
│  (React)        │         │   (FastAPI)      │         │  (S3/MinIO)     │
│                 │         │                  │         │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                     │
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
            ┌──────────────┐ ┌─────────────┐ ┌──────────────┐
            │   Video      │ │   Pose      │ │  Technique   │
            │  Processing  │ │  Detection  │ │  Analysis    │
            │  (OpenCV)    │ │ (MediaPipe) │ │  (Custom)    │
            └──────────────┘ └─────────────┘ └──────────────┘
                    │                │                │
                    └────────────────┼────────────────┘
                                     ▼
                            ┌─────────────────┐
                            │   PostgreSQL    │
                            │   Database      │
                            └─────────────────┘
```

## Component Details

### Frontend Layer

**Technology**: React 18+ with TypeScript

**Responsibilities**:
- User interface for video upload and playback
- Real-time visualization of analysis results
- Dashboard for progress tracking
- User authentication and profile management

**Key Libraries**:
- `react-player` or `video.js` - Video playback
- `three.js` - 3D skeleton visualization
- `recharts` - Data visualization for metrics
- `react-query` - API data fetching and caching

### API Gateway

**Technology**: Python FastAPI

**Responsibilities**:
- RESTful API endpoints for all client operations
- WebSocket support for real-time updates
- Authentication and authorization (JWT)
- Request validation and rate limiting
- Job queue management for video processing

**Endpoints**:
```
POST   /api/v1/videos/upload          - Upload video for analysis
GET    /api/v1/videos/{id}            - Get video details
GET    /api/v1/analysis/{video_id}    - Get analysis results
POST   /api/v1/analysis/{id}/compare  - Compare two analyses
GET    /api/v1/users/{id}/progress    - Get user progress data
```

### Video Processing Pipeline

**Technology**: Python + OpenCV + FFmpeg

**Responsibilities**:
- Video format conversion and normalization
- Frame extraction at specified FPS
- Video quality enhancement (stabilization, brightness)
- Thumbnail generation
- Clip segmentation (isolate individual runs)

**Processing Steps**:
1. Receive uploaded video
2. Validate format and duration
3. Convert to standard format (H.264, 30fps)
4. Extract frames for pose detection
5. Store processed video and frames

### Pose Detection Module

**Technology**: MediaPipe Pose or OpenPose

**Responsibilities**:
- Detect human pose in each frame
- Track 33 body landmarks (MediaPipe) or 25 points (OpenPose)
- Handle occlusions and challenging angles
- Normalize coordinates for consistent analysis

**Key Landmarks for Skiing**:
- Head, shoulders, elbows, wrists
- Hips, knees, ankles
- Feet positioning

**Output Format**:
```json
{
  "frame": 123,
  "timestamp": 4.1,
  "landmarks": [
    {"id": 0, "name": "nose", "x": 0.5, "y": 0.3, "z": -0.1, "visibility": 0.98},
    {"id": 23, "name": "left_hip", "x": 0.45, "y": 0.6, "z": 0.05, "visibility": 0.95},
    ...
  ]
}
```

### Technique Analysis Engine

**Technology**: Python + NumPy + Custom Algorithms

**Responsibilities**:
- Calculate skiing-specific metrics from pose data
- Identify technique issues and strengths
- Generate coaching recommendations
- Score overall performance

**Metrics Calculated**:

1. **Stance Analysis**
   - Hip-ankle alignment (vertical balance)
   - Knee flexion angle
   - Center of mass calculation

2. **Turn Analysis**
   - Turn initiation detection
   - Turn completion timing
   - Inside/outside ski coordination
   - Upper/lower body separation

3. **Edge Control** (requires video angle analysis)
   - Estimated edge angle
   - Carving vs. skidding detection
   - Pressure distribution

4. **Rhythm & Flow**
   - Turn frequency
   - Transition smoothness
   - Speed variation

### Database Schema

**Technology**: PostgreSQL

**Core Tables**:

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    skill_level VARCHAR(20)  -- beginner, intermediate, advanced, expert
);

-- Videos
CREATE TABLE videos (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    filename VARCHAR(255),
    duration FLOAT,
    upload_date TIMESTAMP DEFAULT NOW(),
    processing_status VARCHAR(20),  -- pending, processing, completed, failed
    storage_url TEXT
);

-- Analyses
CREATE TABLE analyses (
    id UUID PRIMARY KEY,
    video_id UUID REFERENCES videos(id),
    created_at TIMESTAMP DEFAULT NOW(),
    pose_data JSONB,  -- Full pose landmark data
    metrics JSONB,    -- Calculated metrics
    recommendations JSONB,  -- AI-generated tips
    overall_score FLOAT
);

-- Progress Tracking
CREATE TABLE progress (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    analysis_id UUID REFERENCES analyses(id),
    date DATE,
    metric_name VARCHAR(50),
    value FLOAT
);
```

## Data Flow

### Video Upload & Analysis Flow

1. **User uploads video** via web interface
2. Frontend sends video to `/api/v1/videos/upload`
3. Backend validates and stores video in object storage (S3/MinIO)
4. Backend creates database record with `processing` status
5. Backend enqueues video processing job
6. **Worker process**:
   - Fetches video from storage
   - Runs video processing pipeline
   - Runs pose detection on frames
   - Runs technique analysis on pose data
   - Stores results in database
   - Updates status to `completed`
7. Frontend polls or receives WebSocket notification
8. User views analysis results with visualizations

## Scalability Considerations

### Current (MVP) Architecture
- Monolithic FastAPI application
- Single worker for video processing
- PostgreSQL on single instance
- Local file storage or single S3 bucket

### Future Scaling Strategies

**When user base grows**:
- Add horizontal scaling with load balancer
- Implement job queue (Celery + Redis/RabbitMQ)
- Multiple worker nodes for parallel processing
- CDN for video delivery
- Database read replicas

**When video processing becomes bottleneck**:
- Distributed processing with Apache Spark or Dask
- GPU instances for ML inference
- Batch processing with scheduled jobs
- Frame-level parallelization

## Security Considerations

1. **Authentication**: JWT-based auth with refresh tokens
2. **Authorization**: Role-based access control (RBAC)
3. **Video Upload**: File type validation, size limits, virus scanning
4. **API Security**: Rate limiting, CORS configuration, HTTPS only
5. **Data Privacy**: Encrypt sensitive data at rest, user data deletion capability

## Deployment Architecture

### Development
```
docker-compose.yml:
  - frontend (React dev server)
  - backend (FastAPI with hot reload)
  - postgres
  - redis
  - minio (S3-compatible storage)
```

### Production
```
- Frontend: Vercel/Netlify (static hosting + CDN)
- Backend: AWS ECS/EKS or DigitalOcean App Platform
- Database: AWS RDS PostgreSQL or managed service
- Storage: AWS S3 with CloudFront CDN
- Workers: Separate ECS tasks or Lambda functions
- Monitoring: Datadog, New Relic, or CloudWatch
```

## Technology Decisions

| Component | Technology Choice | Rationale |
|-----------|------------------|-----------|
| Frontend Framework | React | Large ecosystem, good performance, TypeScript support |
| Backend Framework | FastAPI | Fast, modern Python, automatic OpenAPI docs, async support |
| Pose Detection | MediaPipe | Free, accurate, runs on CPU, good documentation |
| Video Processing | OpenCV + FFmpeg | Industry standard, comprehensive features |
| Database | PostgreSQL | JSONB for flexible schema, strong reliability |
| Object Storage | S3/MinIO | Scalable, cost-effective for large video files |

## Performance Targets

- **Video Upload**: < 30s for 1-minute 1080p video
- **Pose Detection**: ~30 FPS processing speed (real-time capable)
- **Analysis Generation**: < 10s after pose detection complete
- **API Response Time**: < 200ms for read operations
- **Frontend Load Time**: < 2s initial load, < 500ms route changes

## Future Enhancements

1. **Real-time Analysis**: WebRTC streaming for live feedback
2. **Mobile Apps**: React Native for iOS/Android
3. **Multi-camera Sync**: Combine multiple angles for better analysis
4. **Social Features**: Share runs, comment, follow other skiers
5. **Coach Portal**: Tools for coaches to review student progress
6. **AR Overlays**: Real-time feedback overlay on smart goggles
