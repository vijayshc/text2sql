/**
 * Data Mapping Interface JavaScript
 * Handles the AI Data Mapping Analyst interface interactions
 */

class DataMappingInterface {
    constructor() {
        this.currentAnalysisId = null;
        this.analysisResults = {};
        this.mappingData = {};
        
        this.initializeEventListeners();
        this.initializeInterface();
    }
    
    initializeEventListeners() {
        // Single analysis form
        $('#singleAnalysisForm').on('submit', (e) => {
            e.preventDefault();
            this.performSingleAnalysis();
        });
        
        // Bulk analysis
        $('#bulkAnalyzeBtn').on('click', () => {
            this.performBulkAnalysis();
        });
        
        // Bulk columns text area change
        $('#bulkColumns').on('input', () => {
            this.updateBulkColumnCount();
        });
        
        // Catalog overview
        $('#catalogOverviewBtn').on('click', () => {
            this.showCatalogOverview();
        });
        
        // Mapping statistics
        $('#mappingStatsBtn').on('click', () => {
            this.showMappingStats();
        });
        
        // Search mappings
        $('#searchMappingsBtn').on('click', () => {
            this.searchMappings();
        });
        
        // Mapping search on enter
        $('#mappingSearch').on('keypress', (e) => {
            if (e.which === 13) {
                this.searchMappings();
            }
        });
        
        // Status filter change
        $('#mappingStatusFilter').on('change', () => {
            this.searchMappings();
        });
        
        // Save mapping
        $('#saveMappingBtn').on('click', () => {
            this.showSaveMappingModal();
        });
        
        // Confirm save mapping
        $('#confirmSaveMappingBtn').on('click', () => {
            this.saveMapping();
        });
        
        // Tab changes
        $('button[data-bs-toggle="tab"]').on('shown.bs.tab', (e) => {
            const targetTab = $(e.target).attr('data-bs-target');
            if (targetTab === '#mapping-repository') {
                this.loadMappings();
            }
        });
    }
    
    initializeInterface() {
        // Load initial mappings if on repository tab
        this.updateBulkColumnCount();
        
        // Check MCP server availability and show status
        this.checkServerAvailability().then(isAvailable => {
            if (isAvailable) {
                this.showSuccessMessage('Data Mapping MCP server is connected and ready!');
            }
        });
    }
    
    async checkServerAvailability() {
        try {
            // First try the dedicated server status endpoint
            const response = await fetch('/data-mapping/server-status');
            const result = await response.json();

            if (response.ok) {
                if (result.status === 'connected') {
                    // Server is connected and working
                    $('.alert-warning').remove();
                    return true;
                } else {
                    this.showServerUnavailableWarning(result.message || 'MCP server connection issue');
                    return false;
                }
            } else {
                this.showServerUnavailableWarning(result.message || 'MCP server unavailable');
                return false;
            }
        } catch (error) {
            console.warn('Could not check server availability:', error);
            this.showServerUnavailableWarning('Could not connect to data mapping server. Please check if the MCP server is running.');
            return false;
        }
    }
    
    showServerUnavailableWarning(message) {
        // Remove any existing warnings first
        $('.alert-warning').remove();
        
        const alertHtml = `
            <div class="alert alert-warning alert-dismissible fade show" role="alert">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        <strong>MCP Server Issue:</strong> ${message}
                        <br><small class="mt-1 d-block">
                            The Data Mapping MCP server should be registered as "Data Mapping Analyst" at http://localhost:8003.
                            Please check if the server is running and properly registered in the MCP Servers admin panel.
                        </small>
                    </div>
                    <div class="btn-group btn-group-sm ms-3">
                        <button type="button" class="btn btn-outline-warning btn-sm" onclick="dataMappingInterface.recheckServerStatus()">
                            <i class="fas fa-sync-alt"></i> Recheck
                        </button>
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                </div>
            </div>
        `;
        
        this.ensureNotificationContainer();
        $('.notification-container').prepend(alertHtml);
    }
    
    async recheckServerStatus() {
        const isAvailable = await this.checkServerAvailability();
        if (isAvailable) {
            this.showSuccessMessage('✓ Data Mapping MCP server is now connected and ready!');
        }
    }
    
    async performSingleAnalysis() {
        const formData = {
            source_table: $('#sourceTable').val().trim(),
            source_column: $('#sourceColumn').val().trim(),
            target_table: $('#targetTable').val().trim() || undefined,
            target_column: $('#targetColumn').val().trim() || undefined,
            user_context: $('#userContext').val().trim()
        };
        
        if (!formData.source_table || !formData.source_column) {
            this.showAlert('error', 'Source table and column are required');
            return;
        }
        
        this.showLoadingSpinner(true);
        this.showAnalysisProgress();
        
        try {
            this.updateProgressStep('Starting analysis...', 10);
            
            const response = await fetch('/data-mapping/analyze-column', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            if (response.ok && result.status !== 'error') {
                this.updateProgressStep('Analysis complete!', 100);
                this.currentAnalysisId = result.operation_id;
                this.analysisResults[this.currentAnalysisId] = result;
                
                // Show results tab
                setTimeout(() => {
                    $('#results-tab').tab('show');
                    this.displayAnalysisResults(result);
                }, 1000);
            } else {
                this.updateProgressStep('Analysis failed', 0, 'error');
                this.showAlert('error', result.message || 'Analysis failed');
            }
        } catch (error) {
            this.updateProgressStep('Analysis failed', 0, 'error');
            this.showAlert('error', `Analysis failed: ${error.message}`);
        } finally {
            this.showLoadingSpinner(false);
            setTimeout(() => {
                this.hideAnalysisProgress();
            }, 2000);
        }
    }
    
    async performBulkAnalysis() {
        const columnsText = $('#bulkColumns').val().trim();
        if (!columnsText) {
            this.showAlert('error', 'Please enter columns to analyze');
            return;
        }
        
        // Parse columns
        const lines = columnsText.split('\n').filter(line => line.trim());
        const columns = [];
        
        for (const line of lines) {
            const parts = line.trim().split('.');
            if (parts.length >= 2) {
                columns.push({
                    table: parts[0].trim(),
                    column: parts.slice(1).join('.').trim()
                });
            } else {
                this.showAlert('error', `Invalid format in line: ${line}`);
                return;
            }
        }
        
        if (columns.length === 0) {
            this.showAlert('error', 'No valid columns found');
            return;
        }
        
        if (columns.length > 50) {
            this.showAlert('error', 'Bulk analysis limited to 50 columns');
            return;
        }
        
        this.showLoadingSpinner(true);
        $('#bulkAnalyzeBtn').prop('disabled', true).html('<i class="fas fa-spinner fa-spin me-1"></i>Analyzing...');
        
        try {
            const response = await fetch('/data-mapping/bulk-analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ columns: columns })
            });
            
            const result = await response.json();
            
            if (response.ok && result.status !== 'error') {
                this.currentAnalysisId = result.operation_id;
                this.analysisResults[this.currentAnalysisId] = result;
                
                // Show results tab
                $('#results-tab').tab('show');
                this.displayBulkAnalysisResults(result);
                this.showAlert('success', `Bulk analysis completed for ${columns.length} columns`);
            } else {
                this.showAlert('error', result.message || 'Bulk analysis failed');
            }
        } catch (error) {
            this.showAlert('error', `Bulk analysis failed: ${error.message}`);
        } finally {
            this.showLoadingSpinner(false);
            $('#bulkAnalyzeBtn').prop('disabled', false).html('<i class="fas fa-play me-1"></i>Start Bulk Analysis');
        }
    }
    
    async showCatalogOverview() {
        try {
            const response = await fetch('/data-mapping/catalog-overview');
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.displayCatalogOverview(result);
                $('#catalogOverviewModal').modal('show');
            } else {
                this.showAlert('error', result.message || 'Failed to load catalog overview');
            }
        } catch (error) {
            this.showAlert('error', `Failed to load catalog overview: ${error.message}`);
        }
    }
    
    async showMappingStats() {
        try {
            const response = await fetch('/data-mapping/mapping-stats');
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.displayMappingStats(result.stats);
            } else {
                this.showAlert('error', result.message || 'Failed to load mapping statistics');
            }
        } catch (error) {
            this.showAlert('error', `Failed to load mapping statistics: ${error.message}`);
        }
    }
    
    async searchMappings() {
        const searchTerm = $('#mappingSearch').val().trim();
        const statusFilter = $('#mappingStatusFilter').val();
        
        try {
            const params = new URLSearchParams({
                q: searchTerm,
                status: statusFilter
            });
            
            const response = await fetch(`/data-mapping/search-mappings?${params}`);
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                this.displayMappings(result.mappings);
            } else {
                this.showAlert('error', result.message || 'Failed to search mappings');
            }
        } catch (error) {
            this.showAlert('error', `Failed to search mappings: ${error.message}`);
        }
    }
    
    async loadMappings() {
        this.searchMappings(); // Use search with empty criteria to load all
    }
    
    showAnalysisProgress() {
        $('#analysisInstructions').addClass('d-none');
        $('#analysisProgress').removeClass('d-none');
        $('#progressSteps').empty();
    }
    
    hideAnalysisProgress() {
        $('#analysisProgress').addClass('d-none');
        $('#analysisInstructions').removeClass('d-none');
    }
    
    updateProgressStep(message, percentage, type = 'info') {
        $('#analysisProgress .progress-bar').css('width', `${percentage}%`);
        
        const stepHtml = `
            <div class="d-flex align-items-center mb-2">
                <i class="fas fa-${type === 'error' ? 'times text-danger' : 'check text-success'} me-2"></i>
                <span>${message}</span>
            </div>
        `;
        
        $('#progressSteps').append(stepHtml);
    }
    
    updateBulkColumnCount() {
        const text = $('#bulkColumns').val().trim();
        const lines = text ? text.split('\n').filter(line => line.trim()).length : 0;
        $('#bulkColumnCount').text(`${lines} columns`);
    }
    
    displayAnalysisResults(result) {
        let html = `
            <div class="card">
                <div class="card-header d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">
                        <i class="fas fa-chart-line me-2"></i>Analysis Results
                    </h5>
                    <span class="badge bg-${this.getStatusBadgeClass(result.status)}">${result.status}</span>
                </div>
                <div class="card-body">
        `;
        
        // Summary
        html += `
            <div class="row mb-4">
                <div class="col-md-8">
                    <h6>Analysis Summary</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Operation ID:</strong></td><td>${result.operation_id}</td></tr>
                        <tr><td><strong>Status:</strong></td><td>${result.status}</td></tr>
                        <tr><td><strong>Result Type:</strong></td><td>${result.result_type || 'N/A'}</td></tr>
        `;
        
        if (result.target_table && result.target_column) {
            html += `<tr><td><strong>Target:</strong></td><td>${result.target_table}.${result.target_column}</td></tr>`;
        }
        
        if (result.confidence_score) {
            html += `<tr><td><strong>Confidence:</strong></td><td>${(result.confidence_score * 100).toFixed(1)}%</td></tr>`;
        }
        
        html += `
                    </table>
                </div>
                <div class="col-md-4 text-end">
                    ${result.status === 'success' || result.status === 'success_with_aggregation' ? 
                        '<button class="btn btn-primary" onclick="dataMappingInterface.showMappingDetails()"><i class="fas fa-eye me-1"></i>View Details</button>' : ''}
                </div>
            </div>
        `;
        
        // Status-specific content
        if (result.status === 'success' || result.status === 'success_with_aggregation') {
            html += this.renderSuccessfulMapping(result);
        } else if (result.status === 'requires_new_table') {
            html += this.renderNewTableProposal(result);
        } else if (result.status === 'error') {
            html += this.renderError(result);
        }
        
        // Operations log
        if (result.operations_log && result.operations_log.length > 0) {
            html += this.renderOperationsLog(result.operations_log);
        }
        
        html += `
                </div>
            </div>
        `;
        
        $('#resultsContainer').html(html);
        this.mappingData = result;
    }
    
    displayBulkAnalysisResults(result) {
        const statusSummary = result.status_summary || {};
        const detailedResults = result.detailed_results || {};
        
        let html = `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-list me-2"></i>Bulk Analysis Results
                    </h5>
                </div>
                <div class="card-body">
                    <div class="row mb-4">
                        <div class="col-md-6">
                            <h6>Summary</h6>
                            <table class="table table-sm">
                                <tr><td><strong>Total Columns:</strong></td><td>${result.total_columns}</td></tr>
                                <tr><td><strong>Operation ID:</strong></td><td>${result.operation_id}</td></tr>
                                <tr><td><strong>Completed:</strong></td><td>${result.completion_timestamp}</td></tr>
                            </table>
                        </div>
                        <div class="col-md-6">
                            <h6>Status Distribution</h6>
                            <div class="chart-container">
        `;
        
        // Status summary
        for (const [status, count] of Object.entries(statusSummary)) {
            const percentage = (count / result.total_columns * 100).toFixed(1);
            html += `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="badge bg-${this.getStatusBadgeClass(status)}">${status}</span>
                    <span>${count} (${percentage}%)</span>
                </div>
            `;
        }
        
        html += `
                            </div>
                        </div>
                    </div>
                    
                    <h6>Detailed Results</h6>
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>Column</th>
                                    <th>Status</th>
                                    <th>Target</th>
                                    <th>Confidence</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        for (const [column, columnResult] of Object.entries(detailedResults)) {
            const target = columnResult.target_table && columnResult.target_column ? 
                `${columnResult.target_table}.${columnResult.target_column}` : 'N/A';
            const confidence = columnResult.confidence_score ? 
                `${(columnResult.confidence_score * 100).toFixed(1)}%` : 'N/A';
            
            html += `
                <tr>
                    <td><code>${column}</code></td>
                    <td><span class="badge bg-${this.getStatusBadgeClass(columnResult.status)}">${columnResult.status}</span></td>
                    <td>${target}</td>
                    <td>${confidence}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="dataMappingInterface.showColumnDetails('${column}')">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                </tr>
            `;
        }
        
        html += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
        
        $('#resultsContainer').html(html);
        this.mappingData = result;
    }
    
    renderSuccessfulMapping(result) {
        let html = `
            <div class="alert alert-success">
                <h6><i class="fas fa-check-circle me-2"></i>Mapping Found</h6>
                <p class="mb-0">Successfully identified mapping to <strong>${result.target_table}.${result.target_column}</strong></p>
        `;
        
        if (result.status === 'success_with_aggregation') {
            html += `<p class="mb-0 mt-2"><i class="fas fa-exclamation-triangle text-warning me-1"></i>${result.warning}</p>`;
        }
        
        html += `</div>`;
        
        // Mapping logic
        if (result.mapping_logic) {
            html += `
                <div class="mb-3">
                    <h6>ETL Transformation Logic</h6>
                    <div class="bg-light p-3 rounded">
                        <code>${result.mapping_logic.expression}</code>
                    </div>
                    <p class="mt-2 text-muted">${result.mapping_logic.business_rule}</p>
                </div>
            `;
        }
        
        // Join path
        if (result.join_path && result.join_path.path_found) {
            html += `
                <div class="mb-3">
                    <h6>Join Path</h6>
                    <div class="bg-light p-3 rounded">
                        <pre><code>${result.join_path.full_from_clause}</code></pre>
                    </div>
                </div>
            `;
        }
        
        return html;
    }
    
    renderNewTableProposal(result) {
        const proposal = result.table_proposal || {};
        
        return `
            <div class="alert alert-info">
                <h6><i class="fas fa-table me-2"></i>New Table Proposed</h6>
                <p>${result.recommendation}</p>
            </div>
            
            <div class="mb-3">
                <h6>Proposed Table: ${proposal.table_name}</h6>
                <p><strong>Type:</strong> ${proposal.table_type}</p>
                <p><strong>Justification:</strong> ${proposal.justification}</p>
                
                <div class="bg-light p-3 rounded">
                    <h6>DDL Script</h6>
                    <pre><code>${proposal.ddl_script}</code></pre>
                </div>
            </div>
        `;
    }
    
    renderError(result) {
        return `
            <div class="alert alert-danger">
                <h6><i class="fas fa-exclamation-circle me-2"></i>Analysis Error</h6>
                <p>${result.error_message}</p>
                ${result.error_details ? `<pre>${JSON.stringify(result.error_details, null, 2)}</pre>` : ''}
            </div>
        `;
    }
    
    renderOperationsLog(operations) {
        let html = `
            <div class="mt-4">
                <h6>Analysis Steps</h6>
                <div class="timeline">
        `;
        
        operations.forEach((op, index) => {
            html += `
                <div class="timeline-item">
                    <div class="timeline-marker"></div>
                    <div class="timeline-content">
                        <strong>${op.operation}</strong>
                        <p class="mb-1">${op.description}</p>
                        <small class="text-muted">${op.timestamp}</small>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
        
        return html;
    }
    
    displayCatalogOverview(result) {
        const stats = result.catalog_statistics || {};
        const schemaBreakdown = result.schema_breakdown || {};
        
        let html = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Catalog Statistics</h6>
                    <table class="table table-sm">
                        <tr><td>Schemas:</td><td>${stats.schemas || 0}</td></tr>
                        <tr><td>Tables:</td><td>${stats.tables || 0}</td></tr>
                        <tr><td>Columns:</td><td>${stats.columns || 0}</td></tr>
                        <tr><td>Subject Areas:</td><td>${stats.subject_areas || 0}</td></tr>
                        <tr><td>Active Mappings:</td><td>${stats.active_mappings || 0}</td></tr>
                        <tr><td>Total Mappings:</td><td>${stats.total_mappings || 0}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Subject Areas</h6>
                    <ul class="list-unstyled">
        `;
        
        (result.subject_areas || []).forEach(area => {
            html += `<li><i class="fas fa-folder me-2"></i>${area}</li>`;
        });
        
        html += `
                    </ul>
                </div>
            </div>
            
            <h6 class="mt-4">Schema Breakdown</h6>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Schema</th>
                            <th>Tables</th>
                            <th>Table Types</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        for (const [schema, info] of Object.entries(schemaBreakdown)) {
            const tableTypes = Object.entries(info.table_types || {})
                .map(([type, count]) => `${type}: ${count}`)
                .join(', ');
            
            html += `
                <tr>
                    <td><strong>${schema}</strong></td>
                    <td>${info.table_count}</td>
                    <td>${tableTypes}</td>
                </tr>
            `;
        }
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        $('#catalogOverviewContent').html(html);
    }
    
    displayMappings(mappings) {
        const tbody = $('#mappingsTable tbody');
        tbody.empty();
        
        if (mappings.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="8" class="text-center text-muted">No mappings found</td>
                </tr>
            `);
            return;
        }
        
        mappings.forEach(mapping => {
            const row = `
                <tr>
                    <td><code>${mapping.targetTable}</code></td>
                    <td><code>${mapping.targetColumn}</code></td>
                    <td><span class="badge bg-${this.getStatusBadgeClass(mapping.status)}">${mapping.status}</span></td>
                    <td>${mapping.businessRule || 'N/A'}</td>
                    <td>${mapping.version || '1'}</td>
                    <td>${mapping.createdBy || 'Unknown'}</td>
                    <td>${mapping.updatedAt ? new Date(mapping.updatedAt).toLocaleDateString() : 'N/A'}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="dataMappingInterface.viewMappingDetails('${mapping.mappingId}')">
                            <i class="fas fa-eye"></i>
                        </button>
                    </td>
                </tr>
            `;
            tbody.append(row);
        });
    }
    
    showMappingDetails() {
        if (!this.mappingData) return;
        
        // Populate modal with mapping details
        const html = this.generateMappingDetailsHtml(this.mappingData);
        $('#mappingDetailsContent').html(html);
        $('#mappingDetailsModal').modal('show');
    }
    
    showSaveMappingModal() {
        if (!this.mappingData || (!this.mappingData.target_table && !this.mappingData.target_column)) {
            this.showAlert('error', 'No mapping data available to save');
            return;
        }
        
        // Populate form
        $('#saveTargetTable').val(this.mappingData.target_table || '');
        $('#saveTargetColumn').val(this.mappingData.target_column || '');
        $('#saveTransformationLogic').val(this.mappingData.mapping_logic?.expression || '');
        $('#saveBusinessRule').val(this.mappingData.mapping_logic?.business_rule || '');
        $('#saveStatus').val('ACTIVE');
        $('#saveValidatedBy').val('');
        
        $('#saveMappingModal').modal('show');
    }
    
    async saveMapping() {
        const formData = {
            target_table: $('#saveTargetTable').val(),
            target_column: $('#saveTargetColumn').val(),
            transformation_logic: $('#saveTransformationLogic').val(),
            business_rule: $('#saveBusinessRule').val(),
            status: $('#saveStatus').val(),
            validated_by: $('#saveValidatedBy').val(),
            lineage: this.mappingData.lineage || []
        };
        
        try {
            const response = await fetch('/data-mapping/save-mapping', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            if (response.ok && result.status === 'success') {
                $('#saveMappingModal').modal('hide');
                this.showAlert('success', 'Mapping saved successfully');
                
                // Refresh mappings if on repository tab
                if ($('#mapping-repository-tab').hasClass('active')) {
                    this.loadMappings();
                }
            } else {
                this.showAlert('error', result.message || 'Failed to save mapping');
            }
        } catch (error) {
            this.showAlert('error', `Failed to save mapping: ${error.message}`);
        }
    }
    
    getStatusBadgeClass(status) {
        const statusClasses = {
            'success': 'success',
            'success_with_aggregation': 'warning',
            'requires_new_table': 'info',
            'failed_no_path': 'danger',
            'failed_no_match': 'danger',
            'error': 'danger',
            'ACTIVE': 'success',
            'PENDING_VALIDATION': 'warning',
            'INACTIVE': 'secondary'
        };
        
        return statusClasses[status] || 'secondary';
    }
    
    showLoadingSpinner(show) {
        if (show) {
            $('#loadingSpinner').removeClass('d-none');
        } else {
            $('#loadingSpinner').addClass('d-none');
        }
    }
    
    showAlert(type, message) {
        const alertClass = type === 'error' ? 'danger' : type;
        const iconClass = type === 'error' ? 'fa-times-circle' : 
                         type === 'warning' ? 'fa-exclamation-triangle' : 
                         type === 'success' ? 'fa-check-circle' : 'fa-info-circle';
        
        const alertHtml = `
            <div class="alert alert-${alertClass} alert-dismissible fade show" role="alert">
                <i class="fas ${iconClass} me-2"></i>${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        // Create notification container if it doesn't exist
        this.ensureNotificationContainer();
        
        // Insert alert in the notification container
        $('.notification-container').prepend(alertHtml);
        
        // Auto-dismiss after 5 seconds for success messages
        if (type === 'success') {
            setTimeout(() => {
                $('.notification-container .alert-success').first().alert('close');
            }, 5000);
        }
    }
    
    ensureNotificationContainer() {
        if ($('.notification-container').length === 0) {
            $('body').append('<div class="notification-container"></div>');
        }
    }
    
    showSuccessMessage(message) {
        this.showAlert('success', message);
    }
}

// Initialize the interface when DOM is ready
$(document).ready(() => {
    window.dataMappingInterface = new DataMappingInterface();
});
