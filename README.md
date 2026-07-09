# 🎿 Ski Technique Analysis

AI-powered skiing technique analysis using computer vision and biomechanics. Upload a photo of yourself skiing and get instant feedback on your form, aligned with PSIA (Professional Ski Instructors of America) standards.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-orange.svg)](https://mediapipe.dev/)

[Quick Start](#-quick-start) | [Documentation](#-documentation) | [Testing](#-testing) | [Contributing](CONTRIBUTING.md)

---

## 📸 Demo

*Upload a skiing photo → Get instant analysis with skeleton overlay and PSIA-aligned scoring*

**What you get:**
- 🎯 Overall technique score (0-100)
- 📊 Detailed metrics (forward lean, knee flexion, balance, alignment)
- 💡 Personalized coaching recommendations
- 🦴 Skeleton overlay visualization
- ⚖️ PSIA standards alignment

---

## 🎯 Why This Project?

**Problem:** Getting quality feedback on skiing technique is expensive and time-consuming. Ski lessons cost $100-300/hour, and it's hard to objectively measure progress.

**Solution:** Use computer vision and biomechanical analysis to provide instant, objective feedback on skiing technique from just a photo. Perfect for:
- 🎿 Recreational skiers wanting to improve
- 🏫 Ski instructors tracking student progress
- 📈 Athletes analyzing their form
- 🎓 Students learning biomechanics

**Current Status:** ✅ **MVP Complete** - Photo analysis working with 8+ metrics and PSIA-aligned scoring

---

## ✨ Features

### Core Functionality (v1.0)
- ✅ **Photo Upload & Analysis** - Drag-and-drop interface, supports JPG/PNG
- ✅ **Pose Detection** - 33-point skeleton tracking using MediaPipe
- ✅ **PSIA-Aligned Scoring** - Professional ski instructor standards
- ✅ **8+ Biomechanical Metrics:**
  - Forward lean angle (15-25° optimal)
  - Knee flexion (140-160° optimal)
  - Hip-ankle alignment
  - Shoulder level
  - Balance/center of mass
  - Stance width
  - Upper/lower body scores
- ✅ **Visual Overlays** - Skeleton tracking with toggle view
- ✅ **Coaching Recommendations** - AI-generated tips based on analysis
- ✅ **Batch Processing** - Analyze multiple images with CSV export

### Planned Features
- 🔜 Video analysis (frame-by-frame)
- 🔜 Progress tracking over time
- 🔜 User accounts and history
- 🔜 Side-by-side comparisons
- 🔜 Mobile app

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/fireonthemountain/ski-analysis.git
cd ski-analysis

# Start all services
docker-compose up

# Open http://localhost:5173 and upload a skiing photo!
```

### Option 2: Manual Setup

**Prerequisites:**
- Python 3.11+
- Node.js 18+
- PostgreSQL (or use Docker for just the database)

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Database (Docker):**
```bash
docker-compose up -d postgres minio
```

**Access:** Open http://localhost:5173

---

## 🏗️ Architecture

### Tech Stack

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- React Dropzone (file uploads)
- Responsive design

**Backend:**
- Python 3.11 + FastAPI
- MediaPipe (pose detection)
- OpenCV (image processing)
- SQLAlchemy (ORM)
- PostgreSQL (database)
- MinIO/S3 (storage)

**Infrastructure:**
- Docker Compose (local dev)
- RESTful API design
- CORS-enabled for local development

### Project Structure

```
ski-analysis/
├── frontend/               # React web application
│   ├── src/
│   │   ├── components/    # VideoUpload, AnalysisResults, etc.
│   │   ├── App.tsx        # Main app component
│   │   └── ...
│   └── package.json
├── backend/               # Python FastAPI server
│   ├── main.py           # FastAPI app and endpoints
│   ├── analysis/         # Pose detection & technique analysis
│   │   ├── pose_detector.py       # MediaPipe integration
│   │   └── technique_analyzer.py  # PSIA scoring logic
│   ├── database/         # SQLAlchemy models
│   └── requirements.txt
├── scripts/              # Testing and utilities
│   ├── batch_test.py            # Batch image processing
│   └── setup_test_images.sh     # Download test images
├── examples/             # Sample results and data
├── docs/                 # Documentation
│   ├── architecture.md
│   ├── technique-guide.md
│   └── ...
├── docker-compose.yml
├── TESTING.md           # Comprehensive testing guide
└── README.md
```

---

## 📊 How It Works

### Analysis Pipeline

1. **Image Upload** → User uploads skiing photo (JPG/PNG, max 10MB)
2. **Pose Detection** → MediaPipe detects 33 body landmarks
3. **Biomechanical Analysis** → Calculate angles, alignment, balance
4. **PSIA Scoring** → Compare to professional ski instructor standards
5. **Recommendations** → Generate coaching tips based on issues found
6. **Visualization** → Overlay skeleton on original image

### Metrics Explained

| Metric | Optimal Range | What It Measures |
|--------|---------------|------------------|
| Forward Lean | 15-25° | Shin pressure on boot tongue (PSIA standard) |
| Knee Flexion | 140-160° | Athletic stance, shock absorption |
| Balance | 85-95/100 | Center of mass over feet |
| Shoulder Level | <5° tilt | Upper body stability |
| Hip-Ankle Alignment | <10° offset | Vertical stacking |

### Scoring System

- **90-100:** Elite (PSIA Level III demonstration quality)
- **80-89:** Expert (PSIA Level II-III)
- **70-79:** Advanced (PSIA Level I-II)
- **60-69:** Intermediate (working toward Level I)
- **50-59:** Beginner+ (fundamental issues present)
- **<50:** Learning stage

---

## 🧪 Testing

See [TESTING.md](TESTING.md) for comprehensive testing guide and [QUICKSTART_TESTING.md](QUICKSTART_TESTING.md) for quick demo.

### Quick Test

```bash
# 1. Get a skiing photo (full body visible, side/3-4 angle)
# 2. Start the app (see Quick Start above)
# 3. Open http://localhost:5173
# 4. Drag & drop your photo
# 5. View instant analysis with skeleton overlay!
```

### Automated Testing

```bash
# Download curated test images
cd scripts
./setup_test_images.sh

# Run batch analysis
python batch_test.py --input ../test-images --output results.csv
```

**Sample Results:** See [examples/README.md](examples/README.md) for detailed analysis of test results showing scores from 87.3 (expert) to 47.3 (beginner).

---

## 📚 Documentation

- **[TESTING.md](TESTING.md)** - Comprehensive testing guide with PSIA standards
- **[QUICKSTART_TESTING.md](QUICKSTART_TESTING.md)** - Quick testing walkthrough
- **[docs/architecture.md](docs/architecture.md)** - System architecture and design
- **[docs/technique-guide.md](docs/technique-guide.md)** - Skiing technique reference
- **[examples/README.md](examples/README.md)** - Sample results and interpretation
- **[scripts/README.md](scripts/README.md)** - Testing scripts documentation
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute
- **[OPEN_SOURCE_CHECKLIST.md](OPEN_SOURCE_CHECKLIST.md)** - Open source release guide
- **[PRODUCTION_ROADMAP.md](PRODUCTION_ROADMAP.md)** - Commercial product roadmap

---

## 🗺️ Roadmap

### ✅ Phase 1 - MVP (Complete!)
- [x] Photo upload and processing
- [x] Pose detection with MediaPipe
- [x] PSIA-aligned technique analysis
- [x] Skeleton visualization
- [x] Scoring and recommendations
- [x] Batch testing tools
- [x] Comprehensive documentation

### 🔜 Phase 2 - Enhanced Features (Next)
- [ ] Video analysis (frame-by-frame)
- [ ] User authentication and profiles
- [ ] Upload history and progress tracking
- [ ] Side-by-side comparison
- [ ] Download analyzed images
- [ ] PDF report generation

### 🔮 Phase 3 - Advanced
- [ ] Custom ML model training on skiing dataset
- [ ] Terrain recognition (groomed, moguls, powder)
- [ ] Multi-angle photo fusion
- [ ] Coach/student mode
- [ ] Mobile app (iOS/Android)

---

## 🤝 Contributing

Contributions are welcome! This project is ideal for:
- 🐍 Python developers (backend/ML)
- ⚛️ React developers (frontend)
- 🎿 Ski instructors (domain expertise)
- 🧪 Testers (accuracy validation)
- 📝 Technical writers (documentation)

**How to contribute:**

1. Read [CONTRIBUTING.md](CONTRIBUTING.md)
2. Check [open issues](https://github.com/fireonthemountain/ski-analysis/issues)
3. Look for "good first issue" labels
4. Fork, code, test, submit PR!

**Areas needing help:**
- Accuracy validation with real skiers
- Video analysis implementation
- Mobile app development
- UI/UX improvements
- Documentation and tutorials

---

## 📝 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) for details.

**What this means:**
- ✅ Free to use, modify, and distribute
- ✅ Can be used commercially
- ✅ Only requirement: include license notice
- ✅ No warranty provided

---

## 🙏 Acknowledgments

- **[MediaPipe](https://mediapipe.dev/)** - Pose estimation technology
- **[OpenCV](https://opencv.org/)** - Computer vision library
- **[PSIA](https://www.thepsia.org/)** - Professional ski instruction standards
- **Ski instructors and coaches** - Domain expertise and validation
- **Open source community** - For amazing tools and libraries

---

## 🐛 Known Limitations

- 📷 **Camera angle matters:** Side or 3/4 angle works best; front/back views less accurate
- 🖼️ **Static analysis only:** Current version analyzes photos, not video dynamics
- 📏 **Perspective affects measurements:** Metrics can vary ±5-10° based on camera angle
- ⛷️ **Terrain-agnostic:** Doesn't adjust for moguls, powder, park, etc. (yet)
- 👤 **Single person:** Only analyzes one skier per photo

See [TESTING.md](TESTING.md) for detailed accuracy considerations.

---

## 📧 Contact & Support

- **Issues:** [GitHub Issues](https://github.com/fireonthemountain/ski-analysis/issues)
- **Discussions:** [GitHub Discussions](https://github.com/fireonthemountain/ski-analysis/discussions)
- **Project Link:** [https://github.com/fireonthemountain/ski-analysis](https://github.com/fireonthemountain/ski-analysis)

---

## ⭐ Star History

If you find this project useful, please consider giving it a star! It helps others discover the project.

---

**Built with ⛷️ by skiers, for skiers**

*Disclaimer: This tool provides educational feedback and is not a substitute for professional ski instruction. Always ski within your ability and follow mountain safety guidelines.*
