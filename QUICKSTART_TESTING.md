# Quick Start Testing Guide

Get the Ski Analysis app running and test it with real skiing photos in under 10 minutes.

## 🚀 Step 1: Start the Application

### Terminal 1 - Backend
```bash
cd /home/user/Cool-projects/ski-analysis/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Backend should start at: `http://localhost:8000`

### Terminal 2 - Frontend
```bash
cd /home/user/Cool-projects/ski-analysis/frontend
npm install
npm run dev
```

Frontend should start at: `http://localhost:5173`

### Terminal 3 - Database (if needed)
```bash
cd /home/user/Cool-projects/ski-analysis
docker-compose up -d postgres minio
```

## 📸 Step 2: Get Test Images

### Option A: Download Curated Test Images

Here are direct links to skiing photos that should work well for testing:

**Expert/Good Form Images:**
1. [Professional Carver](https://images.unsplash.com/photo-1551698618-1dfe5d97d256?w=800) - Expert technique
2. [Racing Form](https://images.unsplash.com/photo-1605540436563-5bca919ae766?w=800) - High-level racing
3. [Powder Turn](https://images.unsplash.com/photo-1565992441121-4367c2967103?w=800) - Dynamic balance

**Intermediate/Learning Images:**
4. [Beginner Stance](https://images.unsplash.com/photo-1609156724245-5c7e0ad2e60c?w=800) - Common issues
5. [Recreational Skier](https://images.unsplash.com/photo-1551524559-8af4e6624178?w=800) - Intermediate form

**Download Instructions:**
```bash
# Create test directory
mkdir -p /home/user/Cool-projects/ski-analysis/test-images

# Download images using curl or wget
cd /home/user/Cool-projects/ski-analysis/test-images

# Example with wget:
wget "https://images.unsplash.com/photo-1551698618-1dfe5d97d256?w=800" -O expert-carver.jpg
wget "https://images.unsplash.com/photo-1605540436563-5bca919ae766?w=800" -O racing-form.jpg
wget "https://images.unsplash.com/photo-1565992441121-4367c2967103?w=800" -O powder-turn.jpg
wget "https://images.unsplash.com/photo-1609156724245-5c7e0ad2e60c?w=800" -O beginner-stance.jpg
wget "https://images.unsplash.com/photo-1551524559-8af4e6624178?w=800" -O recreational.jpg
```

### Option B: Search and Download Manually

Visit these sites and download 3-5 skiing photos:
- [Unsplash - Skiing](https://unsplash.com/s/photos/skiing)
- [Pexels - Skiing](https://www.pexels.com/search/skiing/)

**Look for photos with:**
- ✅ Full body visible (head to feet)
- ✅ Side view or 3/4 angle
- ✅ Clear, well-lit
- ✅ Person in active skiing stance
- ❌ Avoid: too far away, blurry, straight-on view

## 🧪 Step 3: Run Your First Test

### Using the Web UI

1. Open browser: `http://localhost:5173`
2. Drag and drop a skiing photo
3. Wait 2-3 seconds for analysis
4. Review results:
   - Overall score (0-100)
   - Stance, Balance, Lower/Upper Body scores
   - Key metrics (forward lean, knee flexion, etc.)
   - Coaching recommendations
5. Toggle between "Original" and "Skeleton Overlay" views
6. Click "Analyze Another Photo" to test more images

### Using Batch Testing Script

Process multiple images at once:

```bash
cd /home/user/Cool-projects/ski-analysis/scripts
python batch_test.py --input ../test-images --output results.csv
```

This will:
- Process all images in test-images/ directory
- Generate results.csv with all metrics
- Print summary statistics
- Show top 3 scores

## 📊 Step 4: Interpret Results

### Expected Results by Image Type

**Expert/Professional Skiers:**
```
Overall Score: 80-95
Forward Lean: 18-24°
Knee Flexion: 145-158°
Balance: 85-95
Recommendations: Mostly positive feedback
```

**Intermediate Skiers:**
```
Overall Score: 60-75
Forward Lean: 10-18° or 25-30°
Knee Flexion: 135-170°
Balance: 65-80
Recommendations: Several improvement areas
```

**Beginners/Common Issues:**
```
Overall Score: 40-60
Forward Lean: <10° (sitting back) or >30° (too far forward)
Knee Flexion: >170° (locked) or <130° (over-flexed)
Balance: <65
Recommendations: High-priority fundamentals
```

### Score Interpretation

| Score | Level | Description |
|-------|-------|-------------|
| 90-100 | Elite | Competition/PSIA Level III demonstration quality |
| 80-89 | Expert | PSIA Level II-III range, strong technique |
| 70-79 | Advanced | PSIA Level I-II range, good fundamentals |
| 60-69 | Intermediate | Working toward Level I, adequate technique |
| 50-59 | Beginner+ | Pre-Level I, fundamental issues present |
| <50 | Beginner | Learning stage, needs instruction |

## ✅ Validation Checklist

After testing 3-5 images, verify:

- [ ] All images processed without errors
- [ ] Skeleton overlay shows all body landmarks correctly
- [ ] Scores are in reasonable ranges (30-95)
- [ ] Metrics align with visible technique (e.g., locked knees = high knee flexion angle)
- [ ] Recommendations make sense for the pose
- [ ] Higher-skilled skiers score better than beginners
- [ ] Toggle between original and skeleton works smoothly

## 🔍 Troubleshooting

### "No pose detected in image"
- Ensure full body is visible (head to feet)
- Try better-lit photos
- Make sure skier isn't too small in frame
- Avoid extreme camera angles

### Scores seem inaccurate
- Camera angle affects measurements significantly
- Front/back views don't work well (need side/3-4 angle)
- Clothing/gear obscuring body can confuse detection
- Try different photo of same person

### Backend won't start
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Install missing dependencies
pip install -r requirements.txt

# Check for MediaPipe installation
python -c "import mediapipe; print(mediapipe.__version__)"
```

### Frontend won't start
```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Check Node version (needs 16+)
node --version
```

## 📈 Next Steps After Testing

1. **Document Findings**
   - Which photos worked best?
   - Any unexpected results?
   - Score accuracy vs visual assessment?

2. **Test Edge Cases**
   - Mogul skiing (flexed position)
   - Powder skiing (wider stance)
   - Racing tuck (extreme forward lean)
   - Park/freestyle (unusual positions)

3. **Collect More Data**
   - Test with 20+ diverse images
   - Compare scores across skill levels
   - Validate against PSIA instructor assessments

4. **Iterate on Analysis**
   - Adjust scoring thresholds if needed
   - Refine recommendations
   - Add terrain-specific guidance

## 🎯 Success Criteria

Your testing is successful if:

1. ✅ 80%+ of clear photos are processed successfully
2. ✅ Expert skiers score 15-20 points higher than beginners
3. ✅ Recommendations align with visible technique issues
4. ✅ Skeleton overlay accurately tracks body position
5. ✅ Processing completes in <5 seconds per photo

## 📝 Sample Test Report Template

After testing, document your findings:

```markdown
# Test Results - [Date]

## Images Tested
- Total: 10
- Successful: 9
- Failed: 1

## Score Distribution
- 90-100: 2 images (experts)
- 80-89: 3 images (advanced)
- 70-79: 2 images (intermediate)
- 60-69: 1 image (beginner)
- <60: 1 image (beginner)

## Accuracy Assessment
- Scores aligned with visual assessment: 8/9
- Recommendations were helpful: 9/9
- Skeleton overlay accurate: 8/9

## Issues Found
1. Image #4: No pose detected (skier too far away)
2. Image #7: Shoulder alignment off by ~10° (camera angle issue)

## Recommendations
- Works best with side/3-4 angle photos
- Needs good lighting and full body visible
- Scoring seems accurate for static poses
```

---

**Ready to Test?** Start the app, download a few images, and run your first analysis! 🎿
