# Running Ski Analysis on Your Mac Mini

Complete guide to get the Ski Analysis application running on your Mac mini.

## 📋 Prerequisites

### Required Software

1. **Homebrew** (Package manager for Mac)
```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. **Python 3.11+**
```bash
brew install python@3.11
python3 --version  # Should show 3.11 or higher
```

3. **Node.js 18+**
```bash
brew install node
node --version  # Should show 18 or higher
```

4. **Docker Desktop** (for easy setup)
```bash
# Download from: https://www.docker.com/products/docker-desktop
# Or install via Homebrew:
brew install --cask docker
# Open Docker Desktop from Applications
```

5. **Git**
```bash
brew install git
```

---

## 🚀 Quick Start (Recommended: Docker)

### Step 1: Get the Code

**Option A: Clone from GitHub** (after you push)
```bash
cd ~/Projects  # or wherever you keep projects
git clone https://github.com/fireonthemountain/Movement_Analysis.git
cd Movement_Analysis
```

**Option B: Copy from this session**
```bash
# If you can't push yet, you can transfer the code directly
# The code is ready at: /home/user/Movement_Analysis
# You can download it as a zip or use git bundle
```

### Step 2: Start Everything with Docker

```bash
# Make sure Docker Desktop is running first!

# Start all services (backend, frontend, database, storage)
docker-compose up

# Or run in background:
docker-compose up -d

# Check status:
docker-compose ps
```

### Step 3: Access the Application

Open your browser and go to:
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

### Step 4: Test It!

1. Drag and drop a skiing photo (JPG or PNG)
2. Wait 2-3 seconds for analysis
3. View results with skeleton overlay!

### Stop the Application

```bash
# Stop services
docker-compose down

# Stop and remove all data
docker-compose down -v
```

---

## 🔧 Manual Setup (Without Docker)

If you prefer to run services individually or don't want to use Docker:

### Step 1: Set Up PostgreSQL

**Option A: Use Docker for database only**
```bash
docker-compose up -d postgres minio
```

**Option B: Install PostgreSQL locally**
```bash
brew install postgresql@15
brew services start postgresql@15

# Create database
createdb ski_analysis
```

### Step 2: Set Up Backend

```bash
cd ~/Projects/Movement_Analysis/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
cp ../.env.example .env

# Edit .env with your settings
nano .env
```

**Edit `.env` file:**
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ski_analysis
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=ski-analysis
CORS_ORIGINS=http://localhost:5173
```

**Start backend:**
```bash
python main.py

# Backend will start on http://localhost:8000
```

### Step 3: Set Up Frontend

**Open a new terminal:**

```bash
cd ~/Projects/Movement_Analysis/frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Frontend will start on http://localhost:5173
```

### Step 4: Verify Everything Works

1. Backend: http://localhost:8000/docs (should show API documentation)
2. Frontend: http://localhost:5173 (should show upload interface)
3. Upload a test photo and verify analysis works

---

## 🧪 Running Tests

### Backend Tests

```bash
cd backend
source venv/bin/activate

# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm run test:coverage
```

### Integration Testing

```bash
cd scripts

# Download test images
./setup_test_images.sh

# Run batch analysis
python batch_test.py --input ../test-images --output results.csv

# Review results
open results.csv  # or cat results.csv
```

---

## 🔍 Troubleshooting

### Issue: "Port already in use"

```bash
# Check what's using the port
lsof -i :8000  # Backend port
lsof -i :5173  # Frontend port

# Kill the process if needed
kill -9 <PID>
```

### Issue: "ModuleNotFoundError: No module named 'mediapipe'"

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Docker can't start"

- Make sure Docker Desktop is running
- Check Docker Desktop preferences → Resources
- Allocate at least 4GB RAM

### Issue: "Database connection failed"

```bash
# Check PostgreSQL is running
docker-compose ps

# Or if using local PostgreSQL:
brew services list

# Restart PostgreSQL
brew services restart postgresql@15
```

### Issue: "npm install fails"

```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and try again
rm -rf node_modules package-lock.json
npm install
```

### Issue: "Python version wrong"

```bash
# Install correct Python version
brew install python@3.11

# Use specific version
python3.11 -m venv venv
source venv/bin/activate
python --version  # Should show 3.11.x
```

---

## 📊 Performance on Mac Mini

**Expected performance:**
- M1/M2/M3 Mac Mini: ~1-2 seconds per photo
- Intel Mac Mini (2018+): ~3-5 seconds per photo
- Intel Mac Mini (older): ~5-10 seconds per photo

**If analysis is slow:**
- Close other applications
- Check Activity Monitor for CPU usage
- MediaPipe uses CPU for pose detection (not GPU)

---

## 🎯 Development Workflow

### Recommended Setup

1. **Use Docker for databases** (PostgreSQL, MinIO)
   ```bash
   docker-compose up -d postgres minio
   ```

2. **Run backend manually** (easier to debug)
   ```bash
   cd backend
   source venv/bin/activate
   python main.py
   ```

3. **Run frontend manually** (hot reload for development)
   ```bash
   cd frontend
   npm run dev
   ```

### Code Changes

**Backend changes:**
- Edit Python files in `backend/`
- Restart backend manually (Ctrl+C, then `python main.py`)
- Or use auto-reload: `uvicorn main:app --reload`

**Frontend changes:**
- Edit TypeScript/React files in `frontend/src/`
- Changes auto-reload in browser (Vite hot reload)

### Viewing Logs

```bash
# Docker logs
docker-compose logs -f

# Backend logs (when running manually)
# Shows in terminal where you ran python main.py

# Frontend logs
# Shows in terminal where you ran npm run dev
# Also check browser console (F12)
```

---

## 🌐 Accessing from Other Devices

If you want to access the app from your phone or another computer on your network:

1. **Find your Mac mini's IP address:**
   ```bash
   ipconfig getifaddr en0  # WiFi
   # or
   ipconfig getifaddr en1  # Ethernet
   ```

2. **Update CORS in backend:**
   ```bash
   # Edit backend/.env
   CORS_ORIGINS=http://localhost:5173,http://192.168.1.100:5173
   ```

3. **Update frontend API URL:**
   ```bash
   # Edit frontend/src/App.tsx
   const API_URL = 'http://192.168.1.100:8000'
   ```

4. **Access from other device:**
   - http://192.168.1.100:5173 (use your actual IP)

---

## 💾 Backup and Data

**Application data is stored in:**
- Docker volumes: `docker volume ls`
- Database: PostgreSQL container
- Uploaded files: MinIO container

**Backup everything:**
```bash
# Stop services
docker-compose down

# Backup volumes
docker run --rm -v ski-analysis_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz /data

# Save images
docker run --rm -v ski-analysis_minio_data:/data -v $(pwd):/backup alpine tar czf /backup/minio-backup.tar.gz /data
```

**Reset everything:**
```bash
docker-compose down -v
docker-compose up -d
```

---

## 🎓 Next Steps

Once you have it running:

1. **Test with your own photos:**
   - Use side/3-4 angle photos
   - Full body visible (head to feet)
   - Good lighting

2. **Run batch tests:**
   ```bash
   cd scripts
   ./setup_test_images.sh
   python batch_test.py --input ../test-images --output results.csv
   ```

3. **Read the documentation:**
   - [TESTING.md](TESTING.md) - Testing guide
   - [docs/architecture.md](docs/architecture.md) - How it works
   - [docs/technique-guide.md](docs/technique-guide.md) - PSIA standards

4. **Customize for your needs:**
   - Adjust scoring thresholds in `backend/analysis/technique_analyzer.py`
   - Modify UI in `frontend/src/components/`
   - Add new metrics or features

---

## ❓ Questions?

**Common questions:**

**Q: Can I run this without Docker?**
A: Yes! Follow the "Manual Setup" section above.

**Q: Will this work on Apple Silicon (M1/M2/M3)?**
A: Yes! All dependencies support ARM64.

**Q: How much disk space does it need?**
A: ~2-3GB (Docker images, dependencies, some test data)

**Q: Can I use this offline?**
A: Yes! Once set up, everything runs locally. Only needs internet for initial setup.

**Q: How do I update the code?**
```bash
cd ~/Projects/Movement_Analysis
git pull origin main
docker-compose down
docker-compose up --build
```

---

## 🆘 Getting Help

If you run into issues:

1. Check this guide's troubleshooting section
2. Check [TESTING.md](TESTING.md) for common issues
3. Look at terminal/console logs for error messages
4. Open an issue on GitHub

---

**Ready to get started? Follow the Quick Start section above!** 🎿

---

## Update (November 2026): simplest way to run, and where secrets live

**No Docker needed.** `scripts/run_dev.sh` creates `backend/venv`, uses SQLite and local files under
`backend/data/`, starts the API on port 8003 and the UI on 5177 (both bound to 0.0.0.0) and prints
the LAN URL. The steps above that start PostgreSQL/MinIO are only needed for the Docker stack.

**Docker stack secrets** are no longer written in `docker-compose.yml`. They are read from `.env`:

```bash
cp .env.example .env        # then edit the four change-me values
docker compose config -q    # checks that every required variable is set
docker compose up
```

`POSTGRES_PASSWORD`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` and `SECRET_KEY` are required: compose
stops with a message naming the missing one. `.env` is git-ignored; `.env.example` is the template.
