# Testing Scripts

This directory contains scripts for testing and validating the Ski Analysis application.

## Available Scripts

### 1. `setup_test_images.sh`

Automatically downloads curated skiing photos for testing.

**Usage:**
```bash
cd /home/user/Cool-projects/ski-analysis/scripts
./setup_test_images.sh
```

**What it does:**
- Creates `../test-images/` directory structure
- Downloads 7+ curated skiing photos from Unsplash
- Organizes images by category (good-form, common-issues, terrain-types)
- Validates downloads

**Requirements:**
- `wget` or `curl` installed
- Internet connection

### 2. `batch_test.py`

Processes multiple images and generates CSV report.

**Usage:**
```bash
python batch_test.py --input ../test-images --output results.csv
```

**Parameters:**
- `--input, -i`: Directory containing images (required)
- `--output, -o`: Output CSV file path (default: results.csv)

**What it does:**
- Recursively finds all .jpg, .jpeg, .png images
- Processes each image through pose detection + analysis
- Exports all metrics to CSV
- Prints summary statistics
- Shows top 3 scores

**Output CSV Columns:**
```
filename, status, error,
overall_score, stance_score, balance_score,
lower_body_score, upper_body_score,
forward_lean, knee_flexion, balance,
shoulder_alignment, num_recommendations, pose_quality
```

**Example Output:**
```
🎿 Ski Analysis - Batch Testing
==================================================
Found 12 images to process
Processing...

[1/12] Processing expert-carver.jpg... ✅ Score: 87.3
[2/12] Processing beginner-stance.jpg... ✅ Score: 54.2
[3/12] Processing no-person.jpg... ❌ No pose detected
...

✅ Results saved to results.csv

📊 Summary:
   Total: 12
   Successful: 11
   Failed: 1
   Average Score: 72.4

🏆 Top 3 Scores:
   1. expert-carver.jpg: 87.3
   2. racing-form.jpg: 84.1
   3. powder-turn.jpg: 78.9
```

## Quick Start Workflow

### Full Testing Workflow

```bash
# 1. Download test images
./setup_test_images.sh

# 2. Ensure backend is running
cd ../backend
python main.py  # In separate terminal

# 3. Run batch test
cd ../scripts
python batch_test.py --input ../test-images --output results.csv

# 4. Review results
cat results.csv
# or open in Excel/Google Sheets
```

### Testing Single Category

```bash
# Test only good-form images
python batch_test.py --input ../test-images/good-form --output good-form-results.csv

# Test only beginner issues
python batch_test.py --input ../test-images/common-issues --output issues-results.csv
```

### Progressive Testing

```bash
# Test with your own images
mkdir -p ../test-images/my-photos
# Copy your skiing photos to my-photos/
python batch_test.py --input ../test-images/my-photos --output my-results.csv
```

## Interpreting Results

### Expected Score Ranges

| Image Category | Expected Score | Key Characteristics |
|----------------|----------------|---------------------|
| Expert/Pro | 80-95 | Proper lean (18-24°), flexed knees (145-158°), balanced |
| Advanced | 70-79 | Good fundamentals, minor issues |
| Intermediate | 60-69 | Adequate technique, several improvement areas |
| Beginner | 40-60 | Fundamental issues (sitting back, locked knees) |

### Quality Indicators

**Good Detection (pose_quality: excellent/good):**
- All key landmarks visible
- Skeleton overlay looks accurate
- Metrics in reasonable ranges

**Poor Detection (pose_quality: fair/poor):**
- Missing landmarks
- Scores seem way off
- Try different photo angle or better lighting

## Troubleshooting

### setup_test_images.sh fails

**Error: "wget: command not found" or "curl: command not found"**
```bash
# Install wget on Ubuntu/Debian
sudo apt-get install wget

# Or install curl
sudo apt-get install curl

# On macOS
brew install wget
# or
brew install curl
```

**Error: "Permission denied"**
```bash
chmod +x setup_test_images.sh
./setup_test_images.sh
```

### batch_test.py fails

**Error: "No module named 'analysis'"**
```bash
# Ensure you're running from scripts directory
cd /home/user/Cool-projects/ski-analysis/scripts

# Check Python path
python -c "import sys; print(sys.path)"
```

**Error: "No module named 'mediapipe'"**
```bash
cd ../backend
pip install -r requirements.txt
```

**Error: "No images found"**
```bash
# Check that test-images directory exists and has images
ls -la ../test-images/

# Run setup script if needed
./setup_test_images.sh
```

## Advanced Usage

### Custom Scoring Analysis

```bash
# Filter CSV results for specific score ranges
awk -F',' '$4 >= 80 && $4 <= 100 {print}' results.csv > expert-scores.csv
awk -F',' '$4 >= 60 && $4 < 80 {print}' results.csv > intermediate-scores.csv
awk -F',' '$4 < 60 {print}' results.csv > beginner-scores.csv
```

### Compare Test Runs

```bash
# Test before improvements
python batch_test.py --input ../test-images --output baseline.csv

# Make changes to analysis algorithm
# ... edit technique_analyzer.py ...

# Test after improvements
python batch_test.py --input ../test-images --output improved.csv

# Compare results
diff baseline.csv improved.csv
```

## Additional Resources

- [QUICKSTART_TESTING.md](../QUICKSTART_TESTING.md) - Step-by-step testing guide
- [TESTING.md](../TESTING.md) - Comprehensive testing documentation
- [README.md](../README.md) - Project overview and setup

---

**Questions or Issues?** See main [README.md](../README.md) or open an issue on GitHub.
