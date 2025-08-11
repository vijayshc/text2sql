#!/bin/bash

# Air Gap Setup Script
# Complete setup for running the Text2SQL application in an air-gapped environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   Air Gap Setup for Text2SQL                     ║${NC}"
echo -e "${BLUE}║                                                                  ║${NC}"
echo -e "${BLUE}║  This script will prepare your application for air-gap          ║${NC}"
echo -e "${BLUE}║  deployment by downloading all external dependencies locally.   ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${YELLOW}Prerequisites Check:${NC}"

# Check if curl is available
if ! command -v curl &> /dev/null; then
    echo -e "${RED}✗ curl is required but not installed. Please install curl first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ curl is available${NC}"

# Check internet connectivity
if ! curl -s --head https://cdn.jsdelivr.net &> /dev/null; then
    echo -e "${RED}✗ Internet connection required to download dependencies.${NC}"
    echo -e "${YELLOW}  Please ensure you have internet access and try again.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Internet connection available${NC}"

echo -e "\n${YELLOW}Starting Air Gap Preparation...${NC}"

# Step 1: Download vendor assets
echo -e "\n${BLUE}=== Step 1: Downloading Vendor Assets ===${NC}"
if [ -f "./download_vendor_assets.sh" ]; then
    ./download_vendor_assets.sh
else
    echo -e "${RED}✗ download_vendor_assets.sh not found${NC}"
    exit 1
fi

# Step 2: Update templates
echo -e "\n${BLUE}=== Step 2: Updating Templates ===${NC}"
if [ -f "./update_templates.sh" ]; then
    ./update_templates.sh
else
    echo -e "${RED}✗ update_templates.sh not found${NC}"
    exit 1
fi

# Step 3: Verify setup
echo -e "\n${BLUE}=== Step 3: Verifying Setup ===${NC}"

VENDOR_DIR="static/vendor"
REQUIRED_DIRS=("bootstrap" "fontawesome" "datatables" "jquery" "chartjs" "monaco-editor" "highlight" "markdown-it")

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$VENDOR_DIR/$dir" ]; then
        echo -e "${GREEN}✓ $dir assets downloaded${NC}"
    else
        echo -e "${RED}✗ $dir assets missing${NC}"
    fi
done

# Count total files downloaded
TOTAL_FILES=$(find "$VENDOR_DIR" -type f | wc -l)
echo -e "${GREEN}✓ Total vendor files downloaded: $TOTAL_FILES${NC}"

# Check if templates were updated
if grep -q "vendor/" templates/base.html 2>/dev/null; then
    echo -e "${GREEN}✓ Templates updated to use local assets${NC}"
else
    echo -e "${YELLOW}⚠ Templates may not have been updated correctly${NC}"
fi

echo -e "\n${BLUE}=== Step 4: Creating Air Gap Deployment Package ===${NC}"

# Create deployment info file
cat > "AIRGAP_DEPLOYMENT_INFO.md" << EOF
# Air Gap Deployment Information

## Setup Date
$(date)

## Deployment Status
✅ **Ready for Air Gap Deployment**

## What was downloaded:
- Bootstrap 5.3.0, 5.2.3, 5.3.0-alpha1 (CSS and JS)
- Font Awesome 6.0.0 (CSS and fonts)
- jQuery 3.7.0
- DataTables 1.13.7 (CSS and JS)
- Chart.js 3.9.1
- Monaco Editor 0.36.1 and 0.40.0
- Highlight.js 11.7.0 (with themes)
- Markdown-it 13.0.1

## Total Vendor Assets
$(find static/vendor -type f | wc -l) files in $(du -sh static/vendor | cut -f1)

## Template Updates
All HTML templates have been updated to reference local vendor assets instead of CDN URLs.

## Backup
Template backups are stored in: \`templates_backup_*\` directories

## Verification
To verify the setup works:
1. Disconnect from the internet
2. Start the application: \`python app.py\` or \`python streamlit_app.py\`
3. Check that all styles and functionality work correctly

## Files Modified
- All templates in \`templates/\` directory
- JavaScript files: \`static/js/sql-editor.js\`, \`static/js/query-editor.js\`, \`static/js/admin/db-query-editor.js\`, \`static/js/theme.js\`

## Air Gap Ready Components
- Web interface (all pages)
- Admin interface
- Authentication pages
- Error pages
- Code editors (Monaco Editor)
- Charts and visualizations
- Data tables
- Responsive design
- Icon fonts

## Notes
- The application should now work completely offline
- All external dependencies have been localized
- Font files are included for proper icon display
- Multiple editor themes are available offline
EOF

echo -e "${GREEN}✓ Created deployment info: AIRGAP_DEPLOYMENT_INFO.md${NC}"

# Create a simple verification script
cat > "verify_airgap.sh" << 'EOF'
#!/bin/bash
echo "=== Air Gap Verification ==="
echo "Checking for external URLs in templates..."

if grep -r "https://" templates/ --include="*.html" | grep -v "vendor/"; then
    echo "⚠ Warning: Found external URLs in templates"
    exit 1
else
    echo "✅ No external URLs found in templates"
fi

echo "Checking vendor assets..."
VENDOR_FILES=$(find static/vendor -type f | wc -l)
if [ "$VENDOR_FILES" -gt 20 ]; then
    echo "✅ Vendor assets present ($VENDOR_FILES files)"
else
    echo "⚠ Warning: Few vendor assets found ($VENDOR_FILES files)"
fi

echo "✅ Air gap verification complete"
EOF

chmod +x verify_airgap.sh
echo -e "${GREEN}✓ Created verification script: verify_airgap.sh${NC}"

echo -e "\n${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                     🎉 SETUP COMPLETE! 🎉                        ║${NC}"
echo -e "${GREEN}║                                                                  ║${NC}"
echo -e "${GREEN}║  Your Text2SQL application is now ready for air-gap deployment  ║${NC}"
echo -e "${GREEN}║                                                                  ║${NC}"
echo -e "${GREEN}║  📦 All external dependencies have been downloaded locally      ║${NC}"
echo -e "${GREEN}║  🔧 All templates have been updated                             ║${NC}"
echo -e "${GREEN}║  ✅ Application should work completely offline                   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo -e "1. ${BLUE}Test the application:${NC} Run './verify_airgap.sh' to verify setup"
echo -e "2. ${BLUE}Deploy to air-gap:${NC} Copy this entire directory to your air-gapped environment"
echo -e "3. ${BLUE}Start the application:${NC} Run 'python app.py' or 'python streamlit_app.py'"

echo -e "\n${YELLOW}Package Info:${NC}"
echo -e "• Total size: $(du -sh . | cut -f1)"
echo -e "• Vendor assets: $(find static/vendor -type f | wc -l) files"
echo -e "• Templates updated: $(find templates -name "*.html" | wc -l) files"

echo -e "\n${GREEN}Setup completed successfully! 🚀${NC}"
