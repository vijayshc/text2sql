/**
 * Database Schema Browser
 * Renders a tree view of database objects (tables, views, columns)
 */

class SchemaTreeBuilder {
    constructor(containerElement) {
        this.container = containerElement;
        this.schema = null;
        this.searchInput = document.getElementById('schemaSearch');
        
        if (this.searchInput) {
            this.searchInput.addEventListener('input', () => this.filterTree(this.searchInput.value));
        }
    }
    
    async loadSchema() {
        try {
            const response = await fetch('/admin/database/schema');
            if (!response.ok) {
                throw new Error(`Failed to load schema: ${response.statusText}`);
            }
            
            this.schema = await response.json();
            this.renderTree();
        } catch (error) {
            console.error('Error loading schema:', error);
            this.container.innerHTML = `
                <div class="p-3 text-center text-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    <p>Failed to load database schema.</p>
                    <small>${error.message}</small>
                </div>`;
        }
    }
    
    renderTree() {
        if (!this.schema) return;
        
        this.container.innerHTML = '';
        
        // Create root nodes
        const tablesNode = this._createTreeItem('Tables', 'bi-table', 'tables-root');
        const viewsNode = this._createTreeItem('Views', 'bi-eye', 'views-root');
        
        // Add tables
        const tablesChildren = document.createElement('div');
        tablesChildren.className = 'schema-tree-children';
        tablesChildren.style.display = 'none';
        
        this.schema.tables.forEach(table => {
            const tableNode = this._createTreeItem(
                table.name, 
                'bi-table', 
                `table-${table.name}`,
                'schema-item-table'
            );
            
            // Create columns container
            const columnsContainer = document.createElement('div');
            columnsContainer.className = 'schema-tree-children';
            columnsContainer.style.display = 'none';
            
            // Add columns to table
            table.columns.forEach(column => {
                let iconClass = 'bi-tag';
                let extraClass = 'schema-item-column';
                
                // Check if column is primary key
                if (table.primary_keys && table.primary_keys.includes(column.name)) {
                    iconClass = 'bi-key';
                    extraClass = 'schema-item-pk';
                }
                
                // Check if column is foreign key
                const isForeignKey = table.foreign_keys && table.foreign_keys.some(fk => 
                    fk.constrained_columns && fk.constrained_columns.includes(column.name)
                );
                
                if (isForeignKey) {
                    iconClass = 'bi-link';
                    extraClass = 'schema-item-fk';
                }
                
                const columnNode = this._createTreeItem(
                    `${column.name} (${column.type})`,
                    iconClass,
                    `column-${table.name}-${column.name}`,
                    extraClass,
                    false
                );
                
                // Add column to click for insertion behavior
                columnNode.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (window.sqlEditor) {
                        window.sqlEditor.trigger('keyboard', 'type', {text: column.name});
                    }
                });
                
                columnsContainer.appendChild(columnNode);
            });
            
            // Add toggle behavior for table
            tableNode.querySelector('.schema-tree-toggle').addEventListener('click', (e) => {
                e.stopPropagation();
                const isHidden = columnsContainer.style.display === 'none';
                columnsContainer.style.display = isHidden ? 'block' : 'none';
                e.target.innerHTML = isHidden ? 
                    '<i class="bi bi-dash"></i>' : 
                    '<i class="bi bi-plus"></i>';
            });
            
            // Add table click for insertion behavior
            tableNode.addEventListener('click', (e) => {
                if (window.sqlEditor) {
                    window.sqlEditor.trigger('keyboard', 'type', {text: table.name});
                }
            });
            
            tablesChildren.appendChild(tableNode);
            tablesChildren.appendChild(columnsContainer);
        });
        
        // Add views
        const viewsChildren = document.createElement('div');
        viewsChildren.className = 'schema-tree-children';
        viewsChildren.style.display = 'none';
        
        this.schema.views.forEach(view => {
            const viewNode = this._createTreeItem(
                view.name, 
                'bi-eye', 
                `view-${view.name}`,
                'schema-item-view'
            );
            
            // Create columns container
            const columnsContainer = document.createElement('div');
            columnsContainer.className = 'schema-tree-children';
            columnsContainer.style.display = 'none';
            
            // Add columns to view
            view.columns.forEach(column => {
                const columnNode = this._createTreeItem(
                    `${column.name} (${column.type})`,
                    'bi-tag',
                    `column-${view.name}-${column.name}`,
                    'schema-item-column',
                    false
                );
                
                // Add column to click for insertion behavior
                columnNode.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (window.sqlEditor) {
                        window.sqlEditor.trigger('keyboard', 'type', {text: column.name});
                    }
                });
                
                columnsContainer.appendChild(columnNode);
            });
            
            // Add toggle behavior for view
            viewNode.querySelector('.schema-tree-toggle').addEventListener('click', (e) => {
                e.stopPropagation();
                const isHidden = columnsContainer.style.display === 'none';
                columnsContainer.style.display = isHidden ? 'block' : 'none';
                e.target.innerHTML = isHidden ? 
                    '<i class="bi bi-dash"></i>' : 
                    '<i class="bi bi-plus"></i>';
            });
            
            // Add view click for insertion behavior
            viewNode.addEventListener('click', (e) => {
                if (window.sqlEditor) {
                    window.sqlEditor.trigger('keyboard', 'type', {text: view.name});
                }
            });
            
            viewsChildren.appendChild(viewNode);
            viewsChildren.appendChild(columnsContainer);
        });
        
        // Add toggle behavior for root nodes
        tablesNode.querySelector('.schema-tree-toggle').addEventListener('click', (e) => {
            e.stopPropagation();
            const isHidden = tablesChildren.style.display === 'none';
            tablesChildren.style.display = isHidden ? 'block' : 'none';
            e.target.innerHTML = isHidden ? 
                '<i class="bi bi-dash"></i>' : 
                '<i class="bi bi-plus"></i>';
        });
        
        viewsNode.querySelector('.schema-tree-toggle').addEventListener('click', (e) => {
            e.stopPropagation();
            const isHidden = viewsChildren.style.display === 'none';
            viewsChildren.style.display = isHidden ? 'block' : 'none';
            e.target.innerHTML = isHidden ? 
                '<i class="bi bi-dash"></i>' : 
                '<i class="bi bi-plus"></i>';
        });
        
        // Compose tree
        this.container.appendChild(tablesNode);
        this.container.appendChild(tablesChildren);
        this.container.appendChild(viewsNode);
        this.container.appendChild(viewsChildren);
        
        // Open tables by default
        tablesNode.querySelector('.schema-tree-toggle').click();
    }
    
    _createTreeItem(label, iconClass, id, extraClass = '', isToggleable = true) {
        const item = document.createElement('div');
        item.className = `schema-tree-item ${extraClass || ''}`;
        item.id = id;
        
        let toggleHtml = '';
        if (isToggleable) {
            toggleHtml = `
                <span class="schema-tree-toggle">
                    <i class="bi bi-plus"></i>
                </span>
            `;
        } else {
            toggleHtml = `<span class="schema-tree-toggle" style="visibility:hidden;"></span>`;
        }
        
        item.innerHTML = `
            ${toggleHtml}
            <span class="schema-tree-icon">
                <i class="bi ${iconClass}"></i>
            </span>
            <span class="schema-tree-label">${label}</span>
        `;
        
        return item;
    }
    
    filterTree(searchTerm) {
        if (!searchTerm) {
            // Reset all items to visible
            this.container.querySelectorAll('.schema-tree-item').forEach(item => {
                item.style.display = 'flex';
            });
            return;
        }
        
        searchTerm = searchTerm.toLowerCase();
        
        // Search through all tree items
        this.container.querySelectorAll('.schema-tree-item').forEach(item => {
            const label = item.querySelector('.schema-tree-label').textContent.toLowerCase();
            if (label.includes(searchTerm)) {
                item.style.display = 'flex';
                
                // Make sure parent containers are visible
                let parent = item.parentElement;
                while (parent && parent !== this.container) {
                    parent.style.display = 'block';
                    parent = parent.parentElement;
                }
                
                // Make sure root nodes are visible
                if (item.id.startsWith('table-') || item.id.startsWith('view-') || 
                    item.id.startsWith('column-')) {
                    document.getElementById('tables-root').style.display = 'flex';
                    document.getElementById('views-root').style.display = 'flex';
                }
            } else {
                // Only hide if not a root or container
                if (!item.id.includes('-root')) {
                    item.style.display = 'none';
                }
            }
        });
    }
}

// Initialize when DOM content is loaded
document.addEventListener('DOMContentLoaded', () => {
    const schemaTreeContainer = document.getElementById('schemaTree');
    if (schemaTreeContainer) {
        window.schemaTreeBuilder = new SchemaTreeBuilder(schemaTreeContainer);
        window.schemaTreeBuilder.loadSchema();
    }
});
