#!/bin/bash

# Update Templates Script
# Updates all HTML templates to use local vendor assets instead of CDN links

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Updating Templates to Use Local Vendor Assets ===${NC}"

# Create backup directory
BACKUP_DIR="templates_backup_$(date +%Y%m%d_%H%M%S)"
echo "Creating backup of templates in $BACKUP_DIR..."
cp -r templates "$BACKUP_DIR"

update_file() {
    local file="$1"
    local description="$2"
    
    echo -e "${YELLOW}Updating $description...${NC}"
    
    # Bootstrap CSS replacements
    sed -i 's|https://cdn\.jsdelivr\.net/npm/bootstrap@5\.3\.0/dist/css/bootstrap\.min\.css|{{ url_for('\''static'\'', filename='\''vendor/bootstrap/bootstrap-5.3.0.min.css'\'') }}|g' "$file"
    sed -i 's|https://cdn\.jsdelivr\.net/npm/bootstrap@5\.2\.3/dist/css/bootstrap\.min\.css|{{ url_for('\''static'\'', filename='\''vendor/bootstrap/bootstrap-5.2.3.min.css'\'') }}|g' "$file"
    sed -i 's|https://cdn\.jsdelivr\.net/npm/bootstrap@5\.3\.0-alpha1/dist/css/bootstrap\.min\.css|{{ url_for('\''static'\'', filename='\''vendor/bootstrap/bootstrap-5.3.0-alpha1.min.css'\'') }}|g' "$file"
    
    # Bootstrap JS replacements
    sed -i 's|https://cdn\.jsdelivr\.net/npm/bootstrap@5\.3\.0/dist/js/bootstrap\.bundle\.min\.js|{{ url_for('\''static'\'', filename='\''vendor/bootstrap/bootstrap-5.3.0.bundle.min.js'\'') }}|g' "$file"
    sed -i 's|https://cdn\.jsdelivr\.net/npm/bootstrap@5\.3\.0-alpha1/dist/js/bootstrap\.bundle\.min\.js|{{ url_for('\''static'\'', filename='\''vendor/bootstrap/bootstrap-5.3.0-alpha1.bundle.min.js'\'') }}|g' "$file"
    
    # Font Awesome CSS
    sed -i 's|https://cdnjs\.cloudflare\.com/ajax/libs/font-awesome/6\.0\.0/css/all\.min\.css|{{ url_for('\''static'\'', filename='\''vendor/fontawesome/all.min.css'\'') }}|g' "$file"
    
    # jQuery
    sed -i 's|https://code\.jquery\.com/jquery-3\.7\.0\.min\.js|{{ url_for('\''static'\'', filename='\''vendor/jquery/jquery-3.7.0.min.js'\'') }}|g' "$file"
    
    # DataTables CSS
    sed -i 's|https://cdn\.datatables\.net/1\.13\.7/css/dataTables\.bootstrap5\.min\.css|{{ url_for('\''static'\'', filename='\''vendor/datatables/dataTables.bootstrap5.min.css'\'') }}|g' "$file"
    sed -i 's|https://cdn\.datatables\.net/responsive/2\.5\.0/css/responsive\.bootstrap5\.min\.css|{{ url_for('\''static'\'', filename='\''vendor/datatables/responsive.bootstrap5.min.css'\'') }}|g' "$file"
    
    # DataTables JS
    sed -i 's|https://cdn\.datatables\.net/1\.13\.7/js/jquery\.dataTables\.min\.js|{{ url_for('\''static'\'', filename='\''vendor/datatables/jquery.dataTables.min.js'\'') }}|g' "$file"
    sed -i 's|https://cdn\.datatables\.net/1\.13\.7/js/dataTables\.bootstrap5\.min\.js|{{ url_for('\''static'\'', filename='\''vendor/datatables/dataTables.bootstrap5.min.js'\'') }}|g' "$file"
    sed -i 's|https://cdn\.datatables\.net/responsive/2\.5\.0/js/dataTables\.responsive\.min\.js|{{ url_for('\''static'\'', filename='\''vendor/datatables/dataTables.responsive.min.js'\'') }}|g' "$file"
    sed -i 's|https://cdn\.datatables\.net/responsive/2\.5\.0/js/responsive\.bootstrap5\.min\.js|{{ url_for('\''static'\'', filename='\''vendor/datatables/responsive.bootstrap5.min.js'\'') }}|g' "$file"
    
    # Chart.js
    sed -i 's|https://cdn\.jsdelivr\.net/npm/chart\.js@3\.9\.1/dist/chart\.min\.js|{{ url_for('\''static'\'', filename='\''vendor/chartjs/chart-3.9.1.min.js'\'') }}|g' "$file"
    
    # Markdown-it
    sed -i 's|https://cdnjs\.cloudflare\.com/ajax/libs/markdown-it/13\.0\.1/markdown-it\.min\.js|{{ url_for('\''static'\'', filename='\''vendor/markdown-it/markdown-it-13.0.1.min.js'\'') }}|g' "$file"
    
    # Highlight.js
    sed -i 's|https://cdnjs\.cloudflare\.com/ajax/libs/highlight\.js/11\.7\.0/highlight\.min\.js|{{ url_for('\''static'\'', filename='\''vendor/highlight/highlight-11.7.0.min.js'\'') }}|g' "$file"
    sed -i 's|https://cdnjs\.cloudflare\.com/ajax/libs/highlight\.js/11\.7\.0/styles/github-dark\.min\.css|{{ url_for('\''static'\'', filename='\''vendor/highlight/styles/github-dark.min.css'\'') }}|g' "$file"
    
    # Monaco Editor
    sed -i 's|https://cdnjs\.cloudflare\.com/ajax/libs/monaco-editor/0\.36\.1/min/vs/loader\.min\.js|{{ url_for('\''static'\'', filename='\''vendor/monaco-editor/0.36.1/min/vs/loader.min.js'\'') }}|g' "$file"
    sed -i 's|https://cdnjs\.cloudflare\.com/ajax/libs/monaco-editor/0\.40\.0/min/vs/loader\.min\.js|{{ url_for('\''static'\'', filename='\''vendor/monaco-editor/0.40.0/min/vs/loader.min.js'\'') }}|g' "$file"
    
    echo -e "${GREEN}✓ Updated: $description${NC}"
}

# Update all HTML template files
echo "Finding and updating HTML template files..."

# Main templates
update_file "templates/base.html" "Base template"
update_file "templates/index.html" "Index template"
update_file "templates/query_editor.html" "Query editor template"
update_file "templates/knowledgebase.html" "Knowledge base template"
update_file "templates/agent_mode.html" "Agent mode template"
update_file "templates/samples.html" "Samples template"
update_file "templates/404.html" "404 error template"
update_file "templates/500.html" "500 error template"

# Auth templates
update_file "templates/auth/login.html" "Login template"
update_file "templates/auth/change_password.html" "Change password template"
update_file "templates/auth/reset_request.html" "Reset request template"
update_file "templates/auth/reset_password.html" "Reset password template"

# Admin templates
update_file "templates/admin/base_old.html" "Admin base old template"
update_file "templates/admin/index.html" "Admin index template"
update_file "templates/admin/users.html" "Admin users template"
update_file "templates/admin/user_form.html" "Admin user form template"
update_file "templates/admin/roles.html" "Admin roles template"
update_file "templates/admin/mcp_servers.html" "Admin MCP servers template"
update_file "templates/admin/skills.html" "Admin skills template"
update_file "templates/admin/schema.html" "Admin schema template"
update_file "templates/admin/metadata.html" "Admin metadata template"
update_file "templates/admin/knowledge.html" "Admin knowledge template"
update_file "templates/admin/vector_db.html" "Admin vector DB template"
update_file "templates/admin/config.html" "Admin config template"
update_file "templates/admin/audit_logs.html" "Admin audit logs template"
update_file "templates/admin/db_query_editor.html" "Admin DB query editor template"

# Data mapping templates (if they exist)
if [ -d "templates/data_mapping" ]; then
    for file in templates/data_mapping/*.html; do
        if [ -f "$file" ]; then
            update_file "$file" "Data mapping template: $(basename "$file")"
        fi
    done
fi

# Security templates (if they exist)
if [ -d "templates/security" ]; then
    for file in templates/security/*.html; do
        if [ -f "$file" ]; then
            update_file "$file" "Security template: $(basename "$file")"
        fi
    done
fi

echo -e "\n${YELLOW}=== Updating JavaScript Files ===${NC}"

# Update JavaScript files that reference CDN URLs
update_js_file() {
    local file="$1"
    local description="$2"
    
    echo -e "${YELLOW}Updating $description...${NC}"
    
    # Monaco Editor path updates
    sed -i "s|paths: { 'vs': 'https://cdnjs\.cloudflare\.com/ajax/libs/monaco-editor/0\.36\.1/min/vs' }|paths: { 'vs': '/static/vendor/monaco-editor/0.36.1/min/vs' }|g" "$file"
    sed -i "s|paths: { 'vs': 'https://cdnjs\.cloudflare\.com/ajax/libs/monaco-editor/0\.40\.0/min/vs' }|paths: { 'vs': '/static/vendor/monaco-editor/0.40.0/min/vs' }|g" "$file"
    
    echo -e "${GREEN}✓ Updated: $description${NC}"
}

# Update JS files
update_js_file "static/js/sql-editor.js" "SQL Editor JS"
update_js_file "static/js/query-editor.js" "Query Editor JS"
update_js_file "static/js/admin/db-query-editor.js" "Admin DB Query Editor JS"

# Special handling for theme.js highlight.js URLs
echo -e "${YELLOW}Updating theme.js for local highlight.js themes...${NC}"
sed -i 's|`https://cdnjs\.cloudflare\.com/ajax/libs/highlight\.js/11\.7\.0/styles/\${highlightTheme}\.min\.css`|`/static/vendor/highlight/styles/\${highlightTheme}.min.css`|g' "static/js/theme.js"
echo -e "${GREEN}✓ Updated: theme.js${NC}"

# Update Font Awesome CSS to reference local fonts
echo -e "\n${YELLOW}=== Updating Font Awesome CSS ===${NC}"
if [ -f "static/vendor/fontawesome/all.min.css" ]; then
    # Update font paths in Font Awesome CSS
    sed -i 's|https://cdnjs\.cloudflare\.com/ajax/libs/font-awesome/6\.0\.0/webfonts/|../fontawesome/webfonts/|g' "static/vendor/fontawesome/all.min.css" 2>/dev/null || true
    echo -e "${GREEN}✓ Updated Font Awesome CSS font paths${NC}"
fi

echo -e "\n${GREEN}=== Template Updates Complete ===${NC}"
echo "All templates have been updated to use local vendor assets."
echo -e "${YELLOW}Backup created at: $BACKUP_DIR${NC}"

echo -e "\n${YELLOW}Summary of changes:${NC}"
echo "• Bootstrap CSS/JS → local vendor files"
echo "• Font Awesome CSS → local vendor files"
echo "• jQuery → local vendor files"
echo "• DataTables CSS/JS → local vendor files"
echo "• Chart.js → local vendor files"
echo "• Markdown-it → local vendor files"
echo "• Highlight.js → local vendor files"
echo "• Monaco Editor → local vendor files"
echo "• JavaScript CDN paths → local paths"

echo -e "\n${GREEN}Your application is now ready for air-gap deployment!${NC}"
