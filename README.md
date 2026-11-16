# 🎿 Ski Technique Analysis

Check your own read of a ski run against measurements. Rate what you saw using PSIA-style fundamentals, upload the video or screenshots, and pose estimation tells you where the evidence agrees, disagrees, or cannot say.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10+-orange.svg)](https://mediapipe.dev/)

[Quick Start](#-quick-start) | [Documentation](#-documentation) | [Testing](#-testing) | [Contributing](CONTRIBUTING.md)

---

## What it does now (November 2026): validate your own assessment

You rate a run the way an instructor would (stance width, fore-aft balance, edge angle, angulation,
upper/lower separation, rotation/counter, pole-plant timing, turn shape, ...), upload **one video or a
few screenshots**, and for each rating the app answers:

- **Agrees / Disagrees / Inconclusive**
- the measured value with its uncertainty, and the band thresholds
- a confidence score
- the annotated frames (skeleton overlay) that show it

A low-confidence pose, the wrong camera angle, or a value too close to a threshold gives
*inconclusive* with the reason, never a guessed verdict. Design, metrics and thresholds:
[docs/PIPELINE.md](docs/PIPELINE.md). Current state and test results: [ANALYSIS-2026-11.md](ANALYSIS-2026-11.md).

> Accuracy on real ski footage has not been validated yet. The automated tests use a synthetic
> stick figure with known angles. Check the skeleton overlay on your footage before trusting a number.

---

## 🚀 Quick Start (no Docker, no database server)

Needs Python 3.11–3.13, Node 18+, and `ffmpeg` (`brew install python@3.11 node ffmpeg`).

```bash
cd "ski-analysis"
scripts/run_dev.sh
```

It creates `backend/venv`, installs dependencies, downloads the pose model on first use (~30 MB, from
Google's MediaPipe model host), then prints the URLs, e.g.

```
  Open on this Mac:   http://localhost:5177
  Open on the LAN:    http://192.168.6.89:5177
```

API: port **8003** (`/api/docs`). UI: port **5177**. Both listen on all interfaces.
Data (SQLite, results, annotated frames) lives in `backend/data/`.

### Your first validation

1. Film or pick a clip: **skier coming straight at the camera or going straight away** for edging,
   angulation, separation and turns; **side-on** for fore-aft. One skier, whole body in frame, as large
   as possible. Up to 500 MB; the first 90 s are analysed.
2. Open the UI, drop the video (or 1–40 screenshots: jpg/png/webp/heic).
3. Rate only the items you actually observed. Each rating button shows its numeric band.
4. Leave *Camera view* on Auto-detect unless it guesses wrong.
5. Click **Validate**. The results page shows the agreement table; click a row for its evidence frames,
   and click any chart to jump the annotated video to that moment.

Command line instead of the UI:

```bash
cd backend
./venv/bin/python -m pipeline.cli --list-items
./venv/bin/python -m pipeline.cli --assessment ../examples/assessment.example.json ~/Movies/my_run.mov --out ~/Desktop/my_run_validation
```

Try it without footage (rendered stick figure; MediaPipe does not treat it as a person, so use the
marker estimator): `backend/venv/bin/python scripts/make_sample_media.py`, then
`POSE_ESTIMATOR=marker scripts/run_dev.sh` and upload `examples/synthetic/synthetic_run_front.mp4`.

### Tests

```bash
cd backend && ./venv/bin/python -m pytest tests -q        # 116 tests
cd frontend && npm run build                              # type-check + build
```

### Docker (optional: PostgreSQL + MinIO stack)

```bash
cp .env.example .env      # set the four change-me secrets
docker compose up
```

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
