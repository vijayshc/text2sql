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
