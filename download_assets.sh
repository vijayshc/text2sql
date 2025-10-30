#!/bin/bash

# Script to download external assets and update HTML references

set -e

BASE_DIR="/home/vijay/gitrepo/copilot/text2sql"
VENDOR_DIR="$BASE_DIR/static/vendor"

# Create directories
mkdir -p "$VENDOR_DIR/highlight/languages"
mkdir -p "$VENDOR_DIR/monaco-editor/0.45.0/min/vs"

# Download marked
echo "Downloading marked.min.js..."
curl -s -o "$VENDOR_DIR/marked.min.js" https://cdn.jsdelivr.net/npm/marked/marked.min.js

# Download highlight.js
echo "Downloading highlight.js..."
curl -s -o "$VENDOR_DIR/highlight/highlight.min.js" https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js
curl -s -o "$VENDOR_DIR/highlight/languages/sql.min.js" https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/sql.min.js
curl -s -o "$VENDOR_DIR/highlight/styles/github-dark.min.css" https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css

# Download mermaid
echo "Downloading mermaid.min.js..."
curl -s -o "$VENDOR_DIR/mermaid.min.js" https://cdn.jsdelivr.net/npm/mermaid@10.9.0/dist/mermaid.min.js

# Download Monaco Editor
echo "Downloading Monaco Editor..."
# Use npm to download
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"
npm init -y > /dev/null 2>&1
npm install monaco-editor@0.45.0 > /dev/null 2>&1
cp -r node_modules/monaco-editor/min/vs "$VENDOR_DIR/monaco-editor/0.45.0/min/"
cd /
rm -rf "$TEMP_DIR"

echo "Downloads complete."

# Now update HTML files
echo "Updating HTML references..."

# Function to update file
update_file() {
    local file="$1"
    echo "Updating $file..."
    # Update marked
    sed -i 's|https://cdn.jsdelivr.net/npm/marked/marked.min.js|/static/vendor/marked.min.js|g' "$file"
    # Update highlight.js
    sed -i 's|https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css|/static/vendor/highlight/styles/github-dark.min.css|g' "$file"
    sed -i 's|https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js|/static/vendor/highlight/highlight.min.js|g' "$file"
    sed -i 's|https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/sql.min.js|/static/vendor/highlight/languages/sql.min.js|g' "$file"
    # Update monaco
    sed -i 's|https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs/editor/editor.main.css|/static/vendor/monaco-editor/0.45.0/min/vs/editor/editor.main.css|g' "$file"
    sed -i 's|https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs/loader.js|/static/vendor/monaco-editor/0.45.0/min/vs/loader.js|g' "$file"
    # Update mermaid
    sed -i 's|https://cdn.jsdelivr.net/npm/mermaid@10.9.0/dist/mermaid.min.js|/static/vendor/mermaid.min.js|g' "$file"
}

# Update the HTML files
update_file "$BASE_DIR/templates/code_generator.html"
update_file "$BASE_DIR/templates/base.html"
update_file "$BASE_DIR/templates/index.html"
update_file "$BASE_DIR/templates/admin/file_browser.html"

echo "All updates complete."