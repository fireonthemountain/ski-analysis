#!/bin/bash
#
# Setup Test Images for Ski Analysis
# Downloads curated skiing photos for testing the analysis system
#

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎿 Ski Analysis - Test Image Setup${NC}"
echo "===================================="
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$PROJECT_DIR/test-images"

# Create test directory structure
echo -e "${GREEN}📁 Creating test directory structure...${NC}"
mkdir -p "$TEST_DIR/good-form"
mkdir -p "$TEST_DIR/common-issues"
mkdir -p "$TEST_DIR/terrain-types"

# Check for wget or curl
if command -v wget &> /dev/null; then
    DOWNLOADER="wget"
    DOWNLOAD_CMD="wget -q --show-progress"
elif command -v curl &> /dev/null; then
    DOWNLOADER="curl"
    DOWNLOAD_CMD="curl -L -O"
else
    echo -e "${YELLOW}⚠️  Neither wget nor curl found. Please install one to download images.${NC}"
    echo "You can manually download images from:"
    echo "  - https://unsplash.com/s/photos/skiing"
    echo "  - https://www.pexels.com/search/skiing/"
    exit 1
fi

echo -e "${GREEN}✓ Using $DOWNLOADER for downloads${NC}"
echo ""

# Function to download image
download_image() {
    local url=$1
    local output_path=$2
    local description=$3

    echo -e "${BLUE}Downloading:${NC} $description"

    if [ "$DOWNLOADER" = "wget" ]; then
        wget -q --show-progress "$url" -O "$output_path" 2>&1 | grep -v "Length:" | grep -v "Saving to:" || true
    else
        curl -L --progress-bar "$url" -o "$output_path"
    fi

    if [ -f "$output_path" ]; then
        echo -e "${GREEN}✓ Saved to: $output_path${NC}"
    else
        echo -e "${YELLOW}⚠️  Failed to download: $description${NC}"
    fi
    echo ""
}

# Download expert/good form images
echo -e "${BLUE}📸 Downloading Expert/Good Form Images...${NC}"
echo "========================================"

download_image \
    "https://images.unsplash.com/photo-1551698618-1dfe5d97d256?w=800&q=80" \
    "$TEST_DIR/good-form/expert-carver.jpg" \
    "Expert Carver - Professional technique"

download_image \
    "https://images.unsplash.com/photo-1605540436563-5bca919ae766?w=800&q=80" \
    "$TEST_DIR/good-form/racing-form.jpg" \
    "Racing Form - High-level racing stance"

download_image \
    "https://images.unsplash.com/photo-1565992441121-4367c2967103?w=800&q=80" \
    "$TEST_DIR/good-form/powder-turn.jpg" \
    "Powder Turn - Dynamic balance"

# Download intermediate/common issues images
echo -e "${BLUE}📸 Downloading Intermediate/Learning Images...${NC}"
echo "=============================================="

download_image \
    "https://images.unsplash.com/photo-1609156724245-5c7e0ad2e60c?w=800&q=80" \
    "$TEST_DIR/common-issues/beginner-stance.jpg" \
    "Beginner Stance - Common issues"

download_image \
    "https://images.unsplash.com/photo-1551524559-8af4e6624178?w=800&q=80" \
    "$TEST_DIR/common-issues/recreational.jpg" \
    "Recreational Skier - Intermediate form"

# Download terrain-specific images
echo -e "${BLUE}📸 Downloading Terrain-Specific Images...${NC}"
echo "=========================================="

download_image \
    "https://images.unsplash.com/photo-1571857195320-ea4c3b9e1c16?w=800&q=80" \
    "$TEST_DIR/terrain-types/groomed.jpg" \
    "Groomed Run - Standard conditions"

download_image \
    "https://images.unsplash.com/photo-1586461261039-de9899bb7323?w=800&q=80" \
    "$TEST_DIR/terrain-types/moguls.jpg" \
    "Mogul Skiing - Absorption technique"

# Count downloaded images
TOTAL_IMAGES=$(find "$TEST_DIR" -type f -name "*.jpg" | wc -l)

echo ""
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "=================="
echo -e "Downloaded: ${GREEN}$TOTAL_IMAGES${NC} test images"
echo -e "Location: ${BLUE}$TEST_DIR${NC}"
echo ""
echo -e "${YELLOW}📊 Next Steps:${NC}"
echo "1. Start the application (see QUICKSTART_TESTING.md)"
echo "2. Test individual images via web UI at http://localhost:5173"
echo "3. Or run batch test:"
echo -e "   ${BLUE}cd $SCRIPT_DIR${NC}"
echo -e "   ${BLUE}python batch_test.py --input $TEST_DIR --output results.csv${NC}"
echo ""
echo -e "${GREEN}Happy Testing! 🎿${NC}"
