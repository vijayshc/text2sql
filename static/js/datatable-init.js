/**
 * datatable-init.js
 * Global, opinionate    // Skip specific IDs that are known to have custom initialization
    const id = table.id || '';
    const customManagedTables = [
      'resultsTable', 
      'queryEditorResultsTable',
      'sqlResultsTable',
      'records-table', // Vector DB records with custom pagination
      'collections-table', // Vector DB collections with custom management
      'samplesTable', // Samples page with custom pagination
      'documentsTable', // Knowledge management with custom initialization
      'serversTable' // MCP servers with custom management
    ];s initializer to enforce consistency across pages.
 *
 * Rules:
 * - Initialize any <table> that is visible, has a <thead>, and is not explicitly opted out.
 * - Skip tables that have custom initialization or dynamic lifecycle we already manage.
 * - Apply a unified default config aligned with the index page experience.
 */
(function(){
  // Set global defaults so ALL DataTables (including custom inits) share the same UX
  if (window.jQuery && $.fn.dataTable) {
    $.extend(true, $.fn.dataTable.defaults, {
      // Enable responsive for better mobile experience but disable by default for alignment
      responsive: false,
      autoWidth: false, // Disable automatic column width calculation
      pageLength: 10,
      lengthMenu: [[10, 25, 50, -1], [10, 25, 50, 'All']],
      dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
           '<"row"<"col-sm-12"tr>>' +
           '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
      language: {
        search: 'Filter results:',
        lengthMenu: 'Show _MENU_ entries per page',
        emptyTable: 'No results available'
      },
      // Disable horizontal scroll by default to prevent alignment issues
      scrollX: false,
      scrollCollapse: false,
      // Column definitions for better alignment
      columnDefs: [
        { 
          targets: '_all', 
          className: 'dt-left' // Left align all columns
        },
        { targets: -1, orderable: false, searchable: false } // Last column often contains actions
      ],
      // Ensure proper initialization
      processing: false,
      serverSide: false,
      deferRender: false,
      // Column width calculation
      stateSave: false
    });
  }

  function shouldSkip(table) {
    const $t = $(table);
    
    // Allow opt-out via data attribute
    if ($t.attr('data-table-init') === 'false') return true;
    
    // Skip if already initialized
    if ($.fn.DataTable && $.fn.DataTable.isDataTable(table)) return true;
    
    // Must have a header to build columns properly
    if (!$t.find('thead').length) return true;
    
    // Skip if table has class indicating custom management
    if ($t.hasClass('no-datatable')) return true;
    
    // Skip specific IDs that are known to have custom initialization
    const id = table.id || '';
    const customManagedTables = [
      'resultsTable', 
      'queryEditorResultsTable',
      'sqlResultsTable',
      'records-table', // Vector DB records with custom pagination
      'collections-table', // Vector DB collections with custom management
      'samplesTable', // Samples page with custom pagination
      'documentsTable', // Knowledge management with custom initialization
      'serversTable',
      'skillsTable',
      'recentActivitiesTable' // Admin dashboard table with dynamic content
    ];
    
    if (customManagedTables.includes(id)) return true;
    
    return false;
  }

  function defaultOptions($table) {
    // Basic options consistent with index page and proper alignment
    return {
      // Most options come from global defaults; keep here only minimal safety
      responsive: false,
      autoWidth: false,
      // Force recalculation of column widths
      retrieve: false,
      destroy: false,
      // Ensure proper column alignment
      columnDefs: [
        { 
          targets: '_all', 
          className: 'dt-left'
        }
      ],
      // Callback to fix alignment after draw
      drawCallback: function(settings) {
        // Force column width recalculation
        this.api().columns.adjust();
      },
      initComplete: function(settings, json) {
        // Ensure columns are properly aligned after initialization
        this.api().columns.adjust();
      }
    };
  }

  function enhanceClasses($table) {
    // Ensure Bootstrap table classes are present
    $table.addClass('table table-hover');
    // Remove nowrap class that causes alignment issues
    $table.removeClass('nowrap');
    // Add proper table classes for alignment
    $table.addClass('table-responsive-md');
  }

  function initTables(context) {
    const $scope = context ? $(context) : $(document);
    $scope.find('table').each(function(){
      const table = this;
      if (shouldSkip(table)) return;
      if ($.fn.DataTable && !$.fn.DataTable.isDataTable(table)) {
        const $t = $(table);
        enhanceClasses($t);
        try {
          $t.DataTable(defaultOptions($t));
        } catch (e) {
          // Fail-safe: do not break the page if a table cannot be initialized
          console.warn('DataTable init skipped due to error:', e);
        }
      }
    });
  }

  // Initialize on DOM ready
  $(function(){ 
    initTables(document);
    
    // Add global function to fix DataTable alignment issues
    window.fixDataTableAlignment = function(tableSelector) {
      if (tableSelector) {
        const table = $(tableSelector);
        if ($.fn.DataTable.isDataTable(table)) {
          table.DataTable().columns.adjust().draw();
        }
      } else {
        // Fix alignment for all DataTables
        $('.dataTable').each(function() {
          if ($.fn.DataTable.isDataTable(this)) {
            $(this).DataTable().columns.adjust().draw();
          }
        });
      }
    };
    
    // Auto-fix alignment on window resize
    $(window).on('resize', function() {
      setTimeout(function() {
        window.fixDataTableAlignment();
      }, 100);
    });
  });

  // Optional: observe DOM for dynamically added tables
  const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.addedNodes && m.addedNodes.length) {
        m.addedNodes.forEach(node => {
          if (node.nodeType === 1) { // ELEMENT_NODE
            if (node.tagName === 'TABLE' || node.querySelector?.('table')) {
              initTables(node);
            }
          }
        });
      }
    }
  });

  try {
    observer.observe(document.body, { childList: true, subtree: true });
  } catch (e) {
    // Ignore if not available
  }
})();
