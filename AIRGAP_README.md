# Air Gap Deployment Setup

This repository has been prepared for air-gapped deployment. All external CSS and JavaScript dependencies have been downloaded locally and templates have been updated accordingly.

## 🎯 Quick Start

If you're setting up from scratch in an air-gapped environment:

1. **On a machine WITH internet access:**
   ```bash
   ./setup_airgap.sh
   ```

2. **Copy the entire project to your air-gapped environment**

3. **In the air-gapped environment:**
   ```bash
   # Verify the setup
   ./verify_airgap.sh
   
   # Start the application
   python app.py
   # OR
   python streamlit_app.py
   ```

## 📁 What's Included

### Vendor Assets (`static/vendor/`)
- **Bootstrap** (5.3.0, 5.2.3, 5.3.0-alpha1) - CSS framework
- **Font Awesome** (6.0.0) - Icon fonts
- **jQuery** (3.7.0) - JavaScript library
- **DataTables** (1.13.7) - Table enhancement library
- **Chart.js** (3.9.1) - Charting library
- **Monaco Editor** (0.36.1, 0.40.0) - Code editor
- **Highlight.js** (11.7.0) - Syntax highlighting
- **Markdown-it** (13.0.1) - Markdown parser

### Scripts Provided
- `setup_airgap.sh` - Complete air gap setup (download + update)
- `download_vendor_assets.sh` - Download external dependencies
- `update_templates.sh` - Update templates to use local assets
- `verify_airgap.sh` - Verify air gap setup

## 🔧 How It Works

### Before (External Dependencies)
```html
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
```

### After (Local Dependencies)
```html
<link href="{{ url_for('static', filename='vendor/bootstrap/bootstrap-5.3.0.min.css') }}" rel="stylesheet">
<script src="{{ url_for('static', filename='vendor/jquery/jquery-3.7.0.min.js') }}"></script>
```

## 📊 Statistics

- **Total vendor files:** 43
- **Templates updated:** 29
- **Total package size:** ~30MB
- **Backup created:** `templates_backup_*` directory

## ✅ Features That Work Offline

- ✅ All web pages and styling
- ✅ Admin interface
- ✅ Authentication pages
- ✅ Data tables with sorting/filtering
- ✅ Code editors (SQL, JavaScript)
- ✅ Charts and visualizations
- ✅ Icons and fonts
- ✅ Responsive design
- ✅ Dark/light themes
- ✅ Error pages

## 🔍 Verification

Run the verification script to ensure everything is set up correctly:

```bash
./verify_airgap.sh
```

This checks:
- No external URLs remain in templates
- All vendor assets are present
- Proper file counts

## 🚀 Deployment

1. **Copy the entire project** to your air-gapped environment
2. **Install Python dependencies** (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```
3. **Start the application:**
   ```bash
   python app.py
   ```

## 🔄 Updating Assets

If you need to update any external dependencies:

1. Modify the URLs in `download_vendor_assets.sh`
2. Run `./download_vendor_assets.sh` on a machine with internet
3. Update the corresponding paths in `update_templates.sh`
4. Run `./update_templates.sh`

## 📝 Notes

- **Template backups** are automatically created before updates
- **Font files** are included for proper icon display
- **Multiple versions** of some libraries are supported (Bootstrap, Monaco Editor)
- **All paths** use Flask's `url_for()` for proper URL generation

## ⚠️ Troubleshooting

### If styles don't load:
- Check that vendor files exist: `ls static/vendor/`
- Verify Flask static file serving is working
- Check browser console for 404 errors

### If icons don't show:
- Ensure Font Awesome fonts are in `static/vendor/fontawesome/webfonts/`
- Check CSS paths in Font Awesome CSS file

### If Monaco Editor doesn't work:
- Verify Monaco files in `static/vendor/monaco-editor/`
- Check browser console for module loading errors

## 📞 Support

Check the generated `AIRGAP_DEPLOYMENT_INFO.md` for detailed deployment information and file lists.
