# Testing Guide - Ski Analysis

This guide helps you test the Ski Analysis application with real skiing photos and understand how the analysis aligns with PSIA (Professional Ski Instructors of America) standards.

## 🎯 Quick Start Testing

### 1. Get Sample Images

**Where to Find Good Skiing Photos:**

- **Your Own Photos**: Best for personal analysis
  - Action photos from friends/family skiing
  - GoPro screenshots from ski videos
  - Photos from ski trips

- **Stock Photography** (Free):
  - [Unsplash](https://unsplash.com/s/photos/skiing) - Search "skiing"
  - [Pexels](https://www.pexels.com/search/skiing/) - Free skiing photos
  - [Pixabay](https://pixabay.com/images/search/skiing/) - Royalty-free images

- **Instructional Content**:
  - PSIA website educational materials
  - Ski instructor YouTube channels (screenshots)
  - Ski resort lesson photos

**What Makes a Good Test Photo:**
- ✅ Full body visible (head to feet)
- ✅ Side view or 3/4 angle (not straight-on)
- ✅ Clear, well-lit image
- ✅ Person in skiing stance/turn
- ✅ Minimal obstruction (no poles/trees blocking body)
- ❌ Avoid: too zoomed out, blurry, or extreme angles

### 2. Test Different Scenarios

Create a test folder with images showing different scenarios:

```bash
ski-analysis/
└── test-images/
    ├── good-form/
    │   ├── expert-carving.jpg
    │   ├── proper-stance.jpg
    │   └── balanced-turn.jpg
    ├── common-issues/
    │   ├── sitting-back.jpg
    │   ├── locked-knees.jpg
    │   └── rotation.jpg
    └── terrain-types/
        ├── groomed.jpg
        ├── moguls.jpg
        └── powder.jpg
```

### 3. Expected Results by Scenario

#### **Expert/Good Form**
- Overall Score: 80-95
- Forward Lean: 15-25°
- Knee Flexion: 140-160°
- Balance: 80-100
- Recommendations: Mostly positive feedback

#### **Common Issues**

**Sitting Back (Backseat Skiing)**
- Overall Score: 40-60
- Forward Lean: <10°
- Issue Detected: "Sitting back"
- Recommendation: "Lean forward more from your ankles"

**Locked Knees**
- Overall Score: 50-70
- Knee Flexion: >170°
- Issue Detected: "Knees too straight"
- Recommendation: "Flex your knees more"

**Poor Balance**
- Overall Score: 40-65
- Balance Score: <60
- Issue Detected: "Off-center balance"

## 🎓 PSIA Standards Reference

Our analysis is based on PSIA (Professional Ski Instructors of America) Level I-III standards.

### PSIA Core Movements

**1. Control of Edge Angle** (Not in V1 - static images)
- Edge angle management
- Progressive engagement
- Smooth transitions

**2. Control of Pressure** ✅ (Analyzed)
- **Forward/Aft Balance**: Forward lean angle (15-25° ideal)
- **Inside/Outside Balance**: Weight distribution, balance score
- **Progressive Pressure**: Knee flexion indicates pressure capability

**3. Control of Rotation** ✅ (Analyzed)
- **Upper/Lower Body Separation**: Shoulder alignment
- **Counter**: Hip-ankle alignment
- **Rotary Movements**: Not measurable in static images

**4. Control of Speed** (Not in V1 - requires video)
- Turn shape
- Timing

**5. Flexibility & Range of Motion** ✅ (Analyzed)
- **Knee Flexion**: 140-160° optimal
- **Ankle Flex**: Measured via forward lean
- **Hip Angulation**: Hip-ankle alignment

### PSIA Stance Analysis

Our analysis evaluates these PSIA-defined stance elements:

| PSIA Element | Our Metric | Ideal Range | What We Measure |
|--------------|------------|-------------|-----------------|
| **Athletic Stance** | Knee Flexion | 140-160° | Bend in knees for absorption |
| **Forward Lean** | Forward Lean Angle | 15-25° | Shin pressure on boot tongue |
| **Centered Stance** | Hip-Ankle Alignment | <0.05 normalized | Vertical stacking |
| **Level Shoulders** | Shoulder Alignment | <5° | Upper body stability |
| **Balanced COM** | Balance Score | >80/100 | Center of mass over feet |

### PSIA Levels Alignment

**Level I (Beginner/Intermediate)**
- Focus: Basic stance, balance, wedge turns
- Our Analysis: Identifies fundamental issues (sitting back, locked knees)

**Level II (Advanced/Expert)**
- Focus: Parallel turns, varied terrain, dynamic balance
- Our Analysis: Scores stance quality, separation, balance

**Level III (Expert/Instructor)**
- Focus: All conditions, refined technique, demonstration quality
- Our Analysis: Provides specific metrics for refinement

## 📸 Sample Test Cases

### Test Case 1: Expert Carver
**Expected Metrics:**
```
Forward Lean: 20-25°
Knee Flexion: 145-155°
Balance: 85-95
Shoulder Level: <3°
Overall Score: 85-95
```

**Expected Recommendations:**
- "Good technique!"
- "Maintain this position while skiing dynamically"

### Test Case 2: Backseat Skier
**Expected Metrics:**
```
Forward Lean: 5-8°
Knee Flexion: 160-170°
Balance: 50-65
Overall Score: 45-60
```

**Expected Recommendations:**
- HIGH: "Sitting back - Lean forward from ankles"
- MEDIUM: "Flex knees more for athletic stance"

### Test Case 3: Over-Flexed/Hunched
**Expected Metrics:**
```
Forward Lean: 30-40°
Knee Flexion: 120-130°
Balance: 60-75
Overall Score: 55-70
```

**Expected Recommendations:**
- MEDIUM: "Too far forward - reduce lean slightly"
- MEDIUM: "Over-flexed knees - stand up slightly"

## 🧪 Testing Procedure

### Manual Testing

1. **Start the Application**
```bash
# Terminal 1 - Backend
cd ski-analysis/backend
python main.py

# Terminal 2 - Frontend
cd ski-analysis/frontend
npm run dev
```

2. **Open Browser**
```
http://localhost:5173
```

3. **Test Upload**
- Drag & drop a skiing photo
- Wait for analysis (~2-3 seconds)
- Review results

4. **Verify Results**
- ✅ Skeleton overlay shows all body points
- ✅ Overall score is reasonable (30-95)
- ✅ Metrics make sense for the pose
- ✅ Recommendations align with visible issues
- ✅ Toggle works between original/skeleton

### Batch Testing (Coming Soon)

```bash
# Test multiple images
cd ski-analysis/scripts
python batch_test.py --input ../test-images/ --output results.csv
```

## 🔍 What to Look For

### Good Detection Signs
- ✅ All 33 landmarks visible in skeleton
- ✅ Lines connect body parts correctly
- ✅ Pose looks "locked on" to skier
- ✅ Metrics are in reasonable ranges
- ✅ Recommendations make sense

### Poor Detection Signs
- ❌ Missing landmarks (visibility issues)
- ❌ Landmarks in wrong places
- ❌ Metrics seem way off
- ❌ Error: "No pose detected"

**If Detection Fails:**
- Try different angle/photo
- Ensure full body is visible
- Check lighting isn't too dark
- Make sure skier isn't too small in frame

## 📊 Expected Accuracy

**What Works Well:**
- ✅ Clear, well-lit photos
- ✅ Full body visible
- ✅ Side/3-4 angle views
- ✅ Contrasting colors (skier vs background)
- ✅ Relatively close-up shots

**Limitations:**
- ⚠️ Very distant shots (skier too small)
- ⚠️ Extreme angles (straight from front/back)
- ⚠️ Heavy occlusion (trees, other people)
- ⚠️ Motion blur (use sharper images)
- ⚠️ Low light/dark images

## 🎯 Interpreting Scores

### Overall Score Ranges

**90-100**: Elite/Competition Level
- Nearly perfect technique
- PSIA Level III demonstration quality
- Minor refinements only

**80-89**: Expert/Advanced
- Strong technique
- PSIA Level II/III range
- Some areas for improvement

**70-79**: Advanced Intermediate
- Good fundamentals, room to grow
- PSIA Level I/II range
- Several improvement areas

**60-69**: Intermediate
- Adequate technique with issues
- Working toward PSIA Level I
- Multiple technique issues

**50-59**: Beginner/Intermediate
- Fundamental issues present
- Pre-PSIA Level I
- Needs instruction

**<50**: Beginner/Learning
- Significant technique issues
- Beginner stage
- Focus on basics needed

## 🔬 Advanced Testing

### Compare Against References

1. Find professional ski photos (Olympic skiers, instructors)
2. Upload and analyze
3. Use as baseline for "perfect" scores
4. Compare your photos to these benchmarks

### Progression Tracking

1. Take photos at start of season
2. Analyze and save scores
3. Take lessons, practice
4. Take new photos mid/end of season
5. Compare scores to track improvement

## 📝 Known Limitations (V1)

**Static Image Constraints:**
- ❌ Cannot measure edge angle (camera angle dependent)
- ❌ Cannot assess turn dynamics (need video)
- ❌ Cannot evaluate rhythm/timing
- ❌ Cannot measure speed control
- ❌ One moment in time only

**Future Enhancements:**
- Video analysis for dynamic metrics
- Multiple-angle fusion
- Terrain-aware analysis
- Equipment detection

## 🆘 Troubleshooting

### "No pose detected in image"
**Solutions:**
- Ensure full body visible (head to feet)
- Try better lighting
- Use higher resolution image
- Make sure skier isn't too far away
- Avoid extreme angles

### Scores seem wrong
**Possible Causes:**
- Camera angle affects measurements
- Clothing/gear obscuring body
- Unusual pose or position
- Try different photo of same person

### Skeleton overlay looks weird
**Possible Causes:**
- Low visibility landmarks
- Photo quality issues
- Unusual camera angle
- Try clearer image

## 📚 Additional Resources

**PSIA Standards:**
- [PSIA-AASI Website](https://www.thesnowpros.org/)
- PSIA Alpine Technical Manual
- PSIA Level I-III Exam Guides

**Skiing Technique:**
- Ski Magazine technique articles
- Warren Smith Ski Academy (YouTube)
- Elate Media Ski Tutorials
- Stomp It Tutorials

**Sample Image Sources:**
- Unsplash skiing collection
- Pexels sports photography
- Your own ski trip photos
- Ski school websites

---

**Ready to Test?** Start with 3-5 diverse images and see how the analysis performs!

**Questions or Issues?** Check the main README or open an issue on GitHub.

Happy Testing! 🎿
