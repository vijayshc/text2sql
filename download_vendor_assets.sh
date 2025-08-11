#!/bin/bash

# Air Gap Preparation Script
# Downloads all external CSS and JavaScript dependencies for local use

set -e

VENDOR_DIR="static/vendor"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Creating vendor directories..."
mkdir -p "$VENDOR_DIR"/{bootstrap,fontawesome,datatables,jquery,chartjs,monaco-editor,highlight,markdown-it}

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

download_file() {
    local url="$1"
    local output_path="$2"
    local description="$3"
    
    echo -e "${YELLOW}Downloading $description...${NC}"
    if curl -L --fail --silent --show-error -o "$output_path" "$url"; then
        echo -e "${GREEN}✓ Downloaded: $description${NC}"
    else
        echo -e "${RED}✗ Failed to download: $description${NC}"
        return 1
    fi
}

echo "Starting download of external dependencies..."

# Bootstrap CSS and JS
echo -e "\n${YELLOW}=== Bootstrap Assets ===${NC}"
download_file "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" \
    "$VENDOR_DIR/bootstrap/bootstrap-5.3.0.min.css" \
    "Bootstrap 5.3.0 CSS"

download_file "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js" \
    "$VENDOR_DIR/bootstrap/bootstrap-5.3.0.bundle.min.js" \
    "Bootstrap 5.3.0 JS Bundle"

# Bootstrap 5.2.3 for error pages
download_file "https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css" \
    "$VENDOR_DIR/bootstrap/bootstrap-5.2.3.min.css" \
    "Bootstrap 5.2.3 CSS"

# Bootstrap 5.3.0-alpha1 for admin
download_file "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" \
    "$VENDOR_DIR/bootstrap/bootstrap-5.3.0-alpha1.min.css" \
    "Bootstrap 5.3.0-alpha1 CSS"

download_file "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js" \
    "$VENDOR_DIR/bootstrap/bootstrap-5.3.0-alpha1.bundle.min.js" \
    "Bootstrap 5.3.0-alpha1 JS Bundle"

# Font Awesome
echo -e "\n${YELLOW}=== Font Awesome Assets ===${NC}"
download_file "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" \
    "$VENDOR_DIR/fontawesome/all.min.css" \
    "Font Awesome 6.0.0 CSS"

# Download Font Awesome fonts
mkdir -p "$VENDOR_DIR/fontawesome/webfonts"
font_files=(
    "fa-solid-900.woff2"
    "fa-solid-900.ttf"
    "fa-regular-400.woff2"
    "fa-regular-400.ttf"
    "fa-brands-400.woff2"
    "fa-brands-400.ttf"
    "fa-v4compatibility.woff2"
    "fa-v4compatibility.ttf"
)

for font in "${font_files[@]}"; do
    download_file "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/webfonts/$font" \
        "$VENDOR_DIR/fontawesome/webfonts/$font" \
        "Font Awesome font: $font"
done

# jQuery
echo -e "\n${YELLOW}=== jQuery Assets ===${NC}"
download_file "https://code.jquery.com/jquery-3.7.0.min.js" \
    "$VENDOR_DIR/jquery/jquery-3.7.0.min.js" \
    "jQuery 3.7.0"

# DataTables
echo -e "\n${YELLOW}=== DataTables Assets ===${NC}"
download_file "https://cdn.datatables.net/1.13.7/css/dataTables.bootstrap5.min.css" \
    "$VENDOR_DIR/datatables/dataTables.bootstrap5.min.css" \
    "DataTables Bootstrap5 CSS"

download_file "https://cdn.datatables.net/responsive/2.5.0/css/responsive.bootstrap5.min.css" \
    "$VENDOR_DIR/datatables/responsive.bootstrap5.min.css" \
    "DataTables Responsive Bootstrap5 CSS"

download_file "https://cdn.datatables.net/1.13.7/js/jquery.dataTables.min.js" \
    "$VENDOR_DIR/datatables/jquery.dataTables.min.js" \
    "DataTables Core JS"

download_file "https://cdn.datatables.net/1.13.7/js/dataTables.bootstrap5.min.js" \
    "$VENDOR_DIR/datatables/dataTables.bootstrap5.min.js" \
    "DataTables Bootstrap5 JS"

download_file "https://cdn.datatables.net/responsive/2.5.0/js/dataTables.responsive.min.js" \
    "$VENDOR_DIR/datatables/dataTables.responsive.min.js" \
    "DataTables Responsive JS"

download_file "https://cdn.datatables.net/responsive/2.5.0/js/responsive.bootstrap5.min.js" \
    "$VENDOR_DIR/datatables/responsive.bootstrap5.min.js" \
    "DataTables Responsive Bootstrap5 JS"

# Chart.js
echo -e "\n${YELLOW}=== Chart.js Assets ===${NC}"
download_file "https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js" \
    "$VENDOR_DIR/chartjs/chart-3.9.1.min.js" \
    "Chart.js 3.9.1"

# Markdown-it
echo -e "\n${YELLOW}=== Markdown-it Assets ===${NC}"
download_file "https://cdnjs.cloudflare.com/ajax/libs/markdown-it/13.0.1/markdown-it.min.js" \
    "$VENDOR_DIR/markdown-it/markdown-it-13.0.1.min.js" \
    "Markdown-it 13.0.1"

# Highlight.js
echo -e "\n${YELLOW}=== Highlight.js Assets ===${NC}"
download_file "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js" \
    "$VENDOR_DIR/highlight/highlight-11.7.0.min.js" \
    "Highlight.js 11.7.0"

# Highlight.js themes
mkdir -p "$VENDOR_DIR/highlight/styles"
for theme in github-dark.min.css github.min.css default.min.css; do
    download_file "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/$theme" \
        "$VENDOR_DIR/highlight/styles/$theme" \
        "Highlight.js theme: $theme"
done

# Monaco Editor
echo -e "\n${YELLOW}=== Monaco Editor Assets ===${NC}"
MONACO_VERSION_036="0.36.1"
MONACO_VERSION_040="0.40.0"

# Download Monaco Editor 0.36.1 (used in most places)
mkdir -p "$VENDOR_DIR/monaco-editor/$MONACO_VERSION_036/min/vs"
download_file "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/$MONACO_VERSION_036/min/vs/loader.min.js" \
    "$VENDOR_DIR/monaco-editor/$MONACO_VERSION_036/min/vs/loader.min.js" \
    "Monaco Editor $MONACO_VERSION_036 Loader"

# Download Monaco Editor 0.40.0 (used in admin db query editor)
mkdir -p "$VENDOR_DIR/monaco-editor/$MONACO_VERSION_040/min/vs"
download_file "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/$MONACO_VERSION_040/min/vs/loader.min.js" \
    "$VENDOR_DIR/monaco-editor/$MONACO_VERSION_040/min/vs/loader.min.js" \
    "Monaco Editor $MONACO_VERSION_040 Loader"

# Download Monaco Editor core files for both versions
for version in "$MONACO_VERSION_036" "$MONACO_VERSION_040"; do
    echo "Downloading Monaco Editor $version core files..."
    
    # Essential Monaco files
    monaco_files=(
        "editor/editor.main.css"
        "editor/editor.main.js"
        "editor/editor.main.nls.js"
        "base/browser/ui/codicons/codicon/codicon.ttf"
        "base/common/worker/simpleWorker.js"
        "language/json/json.worker.js"
        "language/css/css.worker.js"
        "language/html/html.worker.js"
        "language/typescript/ts.worker.js"
    )
    
    for file in "${monaco_files[@]}"; do
        mkdir -p "$VENDOR_DIR/monaco-editor/$version/min/vs/$(dirname "$file")"
        download_file "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/$version/min/vs/$file" \
            "$VENDOR_DIR/monaco-editor/$version/min/vs/$file" \
            "Monaco $version: $file"
    done
done

echo -e "\n${GREEN}=== Download Complete ===${NC}"
echo "All vendor assets have been downloaded to $VENDOR_DIR/"

echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Run the update_templates.sh script to update all templates to use local files"
echo "2. Test your application in an air-gapped environment"

# Create a simple index file for reference
cat > "$VENDOR_DIR/README.md" << 'EOF'
# Vendor Assets for Air-Gap Deployment

This directory contains all external CSS and JavaScript dependencies downloaded for air-gap deployment.

## Directory Structure

- `bootstrap/` - Bootstrap CSS and JS files (multiple versions)
- `fontawesome/` - Font Awesome CSS and font files
- `datatables/` - DataTables CSS and JS files
- `jquery/` - jQuery library
- `chartjs/` - Chart.js library
- `monaco-editor/` - Monaco Editor files (multiple versions)
- `highlight/` - Highlight.js library and themes
- `markdown-it/` - Markdown-it parser

## Usage

All templates have been updated to reference these local files instead of CDN URLs.
The application should now work in an air-gapped environment.
EOF

echo -e "${GREEN}Created vendor asset index: $VENDOR_DIR/README.md${NC}"
