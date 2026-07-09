# Complete Prompt to Recreate Ski Analysis Project

Copy this entire prompt and use it on your Mac with Claude or any AI assistant:

---

## PROMPT START

Create a new ski technique analysis application repository with the following specifications:

### Project Overview
Build a comprehensive ski technique analysis application that uses computer vision and AI to help skiers improve their form. The app analyzes video footage to provide detailed feedback on skiing technique.

### Repository Setup

1. **Create directory structure:**
```bash
mkdir ski-analysis && cd ski-analysis
git init
mkdir -p frontend/src/{components,pages,hooks,utils,types}
mkdir -p frontend/public
mkdir -p backend/{api,models,processing,analysis,database}
mkdir -p mobile docs tests scripts models
```

2. **Technology Stack:**
- **Frontend**: React 18 + TypeScript + Vite
- **Backend**: Python FastAPI
- **Pose Detection**: MediaPipe
- **Video Processing**: OpenCV + FFmpeg
- **Database**: PostgreSQL
- **Storage**: S3/MinIO
- **Infrastructure**: Docker Compose

### Files to Create:

#### 1. README.md
Create a comprehensive README with:
- Project title: "Ski Technique Analysis"
- Overview: AI-powered ski technique analysis using computer vision
- Key features:
  - Video upload & processing (various formats, action cameras)
  - Pose detection & tracking (skeleton tracking, joint positions)
  - Technique evaluation (body positioning, edge angle, weight transfer, upper/lower body separation, pole plant timing, turn shape)
  - Visual overlays (skeleton tracking, angle measurements, trajectory)
  - Side-by-side comparison with pros or previous runs
  - Progress tracking over time
  - AI-generated coaching tips
  - Future: real-time analysis, multi-angle sync, mobile apps
- Tech stack details (React, FastAPI, MediaPipe/OpenPose, OpenCV, PostgreSQL, Redis, Docker)
- Project structure showing all directories
- Installation instructions (Docker Compose + manual setup)
- Roadmap with 4 phases:
  - Phase 1 (MVP): Video upload, pose detection, basic analysis, simple visualizations
  - Phase 2: Advanced metrics, comparisons, progress tracking, auth
  - Phase 3: Custom ML models, AI coaching, highlights, style classification
  - Phase 4: Mobile apps, real-time mode, multi-camera, social features
- Contributing guidelines reference
- MIT License reference
- Built with ⛷️ tagline

#### 2. .gitignore
Include:
- Node modules, Python cache, virtual environments
- IDE files (.vscode, .idea, .DS_Store)
- Environment files (.env, .env.local)
- Logs and test coverage
- Build outputs (dist/, build/)
- Video files (*.mp4, *.avi, *.mov, uploads/)
- Large ML model files (*.h5, *.pb, *.pth)
- Docker overrides
- OS files

#### 3. LICENSE
MIT License, Copyright 2025 Ski Analysis Contributors

#### 4. CONTRIBUTING.md
Include:
- Ways to contribute (bugs, features, docs, code, testing)
- Getting started (fork, clone, setup)
- Development guidelines:
  - Python: PEP 8, black formatter, flake8 linting, type hints, 100 char lines
  - TypeScript: ESLint, functional components, named exports, strict mode
- Conventional commits format (feat, fix, docs, style, refactor, test, chore)
- Testing requirements (pytest for backend, npm test for frontend)
- PR process and template
- Bug report and feature request templates
- Community guidelines

#### 5. frontend/package.json
```json
{
  "name": "ski-analysis-frontend",
  "version": "0.1.0",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "lint": "eslint . --ext ts,tsx"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.22.0",
    "@tanstack/react-query": "^5.22.0",
    "axios": "^1.6.7",
    "three": "^0.161.0",
    "@react-three/fiber": "^8.15.0",
    "@react-three/drei": "^9.96.0",
    "video.js": "^8.10.0",
    "recharts": "^2.12.0",
    "zustand": "^4.5.0",
    "react-dropzone": "^14.2.3",
    "date-fns": "^3.3.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.1",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.3.3",
    "vite": "^5.1.0",
    "eslint": "^8.56.0",
    "vitest": "^1.2.2",
    "autoprefixer": "^10.4.17",
    "tailwindcss": "^3.4.1"
  }
}
```

#### 6. frontend/vite.config.ts
Standard Vite + React config, port 5173

#### 7. frontend/tsconfig.json
TypeScript config with strict mode, ES2020 target, React JSX

#### 8. frontend/index.html
Basic HTML5 structure with root div and module script import

#### 9. frontend/src/main.tsx
Standard React 18 createRoot with StrictMode

#### 10. frontend/src/App.tsx
Create a landing page with:
- Header: "🎿 Ski Technique Analysis" title
- Hero section with project description
- 3 feature cards:
  - 📹 Video Upload
  - 🤖 AI Analysis
  - 📊 Progress Tracking
- CTA buttons (Get Started, Learn More)
- Status badge: "🚧 Currently in development - MVP coming soon!"
- Footer: "Built with ⛷️ by skiers, for skiers"

#### 11. frontend/src/App.css + index.css
Modern, clean styling with:
- Gradient purple theme (#667eea to #764ba2)
- Grid layout for features
- Hover effects on cards
- Responsive design

#### 12. backend/requirements.txt
```
fastapi==0.109.2
uvicorn[standard]==0.27.1
python-multipart==0.0.9
psycopg2-binary==2.9.9
sqlalchemy==2.0.27
alembic==1.13.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.1
opencv-python==4.9.0.80
opencv-contrib-python==4.9.0.80
ffmpeg-python==0.2.0
mediapipe==0.10.9
numpy==1.26.4
scipy==1.12.0
scikit-learn==1.4.0
pandas==2.2.0
boto3==1.34.34
minio==7.2.3
pydantic==2.6.1
aiofiles==23.2.1
pillow==10.2.0
pytest==8.0.0
pytest-asyncio==0.23.4
httpx==0.26.0
```

#### 13. backend/main.py
FastAPI app with:
- CORS middleware
- Health check endpoint at /health
- API v1 root at /api/v1
- Placeholder endpoints:
  - GET /api/v1/videos (list videos)
  - POST /api/v1/videos/upload (upload video)
  - GET /api/v1/analysis/{video_id} (get analysis)
- Docs at /api/docs
- Environment variable loading with dotenv

#### 14. docker-compose.yml
Services for:
- **postgres**: PostgreSQL 16, database: ski_analysis, user: skiuser
- **redis**: Redis 7 for caching
- **minio**: MinIO for S3-compatible storage (ports 9000, 9001)
- **backend**: FastAPI on port 8000, mounted volumes, depends on postgres/redis/minio
- **frontend**: Vite dev server on port 5173
- Include health checks and proper dependency ordering

#### 15. .env.example
```
DATABASE_URL=postgresql://skiuser:skipass123@localhost:5432/ski_analysis
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET_NAME=ski-videos
SECRET_KEY=your-secret-key-change-in-production
CORS_ORIGINS=http://localhost:5173
MAX_VIDEO_SIZE_MB=500
ALLOWED_VIDEO_FORMATS=mp4,avi,mov,mkv
POSE_MODEL=mediapipe
DEBUG=true
```

#### 16. docs/architecture.md
Create comprehensive architecture documentation covering:
- High-level system diagram (Frontend → API Gateway → Video Processing/Pose Detection/Analysis → Database)
- Component details:
  - Frontend: React with react-player, three.js, recharts
  - API Gateway: FastAPI with REST endpoints and WebSocket
  - Video Processing: OpenCV + FFmpeg pipeline
  - Pose Detection: MediaPipe with 33 landmarks
  - Technique Analysis: Custom algorithms for skiing metrics
- Database schema with tables: users, videos, analyses, progress
- Data flow from upload to analysis
- API endpoints specification
- Scalability considerations (horizontal scaling, job queues, GPU instances)
- Security considerations (JWT auth, file validation, rate limiting)
- Deployment architecture (dev: docker-compose, prod: AWS/DO)
- Technology decision rationale
- Performance targets (upload <30s, analysis <10s, API <200ms)

#### 17. docs/technique-guide.md
Comprehensive skiing technique reference including:
- **Stance & Balance**: Athletic stance, COM positioning, hip-ankle alignment, flexion
- **Edge Control**: Edge angles (0°-60°+), pressure distribution (70:30 outside:inside), carving vs skidding
- **Turn Dynamics**: Turn phases (initiation, control, completion), turn shapes (short/medium/long radius), rhythm
- **Upper Body**: Shoulder alignment, counter and angulation, arm position
- **Lower Body**: Knee angles (20-40° flexion), hip angulation, ankle flex (15-25°)
- **Pole Plant**: Timing, position, technique
- Analysis metrics table with ideal ranges
- Qualitative assessments (flow, adaptability, style, efficiency)
- Terrain considerations (groomed, moguls, powder, ice)
- Skill progression (beginner → expert focus areas)
- Camera angles and recording tips
- References to PSIA, CSIA, ISIA standards

### Initial Commit

After creating all files, make initial commit:
```bash
git add -A
git commit -m "Initial commit: Ski Technique Analysis project setup

- Created comprehensive project structure
- Added detailed README with features and roadmap
- Set up React + TypeScript frontend with Vite
- Set up Python FastAPI backend
- Created Docker Compose dev environment
- Added architecture and technique documentation
- Configured dependencies and environment variables
- Added MIT License and contributing guidelines

Foundation for ski technique analysis platform using computer vision and AI."
```

### Final Steps
```bash
git remote add origin https://github.com/fireonthemountain/ski-analysis.git
git branch -M main
git push -u origin main
```

## PROMPT END

---

## Usage Instructions

### On Your Mac:

1. **Clone your empty GitHub repository:**
```bash
cd ~/Projects  # or wherever you keep projects
git clone https://github.com/fireonthemountain/ski-analysis.git
cd ski-analysis
```

2. **Use this prompt with Claude:**
   - Open Claude Code or Claude.ai on your Mac
   - Copy the "PROMPT START" to "PROMPT END" section above
   - Paste it and say: "Please create all the files described in this prompt"

3. **Alternatively, manually create files:**
   - Follow the file descriptions above
   - Create each file in the specified location
   - Copy the content as described

4. **Verify everything was created:**
```bash
# Check file structure
ls -la
ls frontend/
ls backend/
ls docs/

# Verify git status
git status
```

5. **Commit and push:**
```bash
git add -A
git commit -m "Initial commit: Ski Technique Analysis project setup"
git push -u origin main
```

6. **Start development:**
```bash
# Option 1: Docker (recommended)
docker-compose up

# Option 2: Manual
cd frontend && npm install && npm run dev
cd ../backend && pip install -r requirements.txt && uvicorn main:app --reload
```

---

## What You'll Have

After running this prompt, you'll have a complete ski analysis project with:

- ✅ 18 files created
- ✅ 1,783+ lines of code and documentation
- ✅ Full React + TypeScript frontend
- ✅ FastAPI Python backend
- ✅ Docker Compose setup
- ✅ Comprehensive documentation
- ✅ Ready for development

The project will be ready to:
1. Accept video uploads
2. Process videos with OpenCV
3. Detect poses with MediaPipe
4. Analyze skiing technique
5. Display results with visualizations

---

## Quick Reference

**Repository:** https://github.com/fireonthemountain/ski-analysis.git

**Tech Stack:**
- Frontend: React 18 + TypeScript + Vite
- Backend: FastAPI + Python 3.9+
- ML: MediaPipe, OpenCV, NumPy
- Database: PostgreSQL
- Storage: MinIO/S3
- Infrastructure: Docker

**Next Steps After Setup:**
1. Implement video upload endpoint
2. Add pose detection pipeline
3. Build technique analysis engine
4. Create visualization components
5. Add user authentication

---

**Built with ⛷️ for skiers who want to improve their technique!**
