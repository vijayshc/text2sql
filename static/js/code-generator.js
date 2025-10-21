/**
 * Code Generator JavaScript
 * Handles UI interactions and API calls for code generation
 */

class CodeGenerator {
    constructor() {
        this.currentOperationId = null;
        this.progressInterval = null;
        
        this.initializeElements();
        this.attachEventListeners();
        this.loadProjects();
    }
    
    initializeElements() {
        // Form elements
        this.projectSelect = document.getElementById('projectSelect');
        this.userPrompt = document.getElementById('userPrompt');
        this.generateBtn = document.getElementById('generateBtn');
        this.resetBtn = document.getElementById('resetBtn');
        this.refreshBtn = document.getElementById('refreshBtn');
        
        // Cards
        this.progressCard = document.getElementById('progressCard');
        this.resultsCard = document.getElementById('resultsCard');
        this.errorCard = document.getElementById('errorCard');
        this.loadingSpinner = document.getElementById('loadingSpinner');
        
        // Progress elements
        this.progressBar = document.getElementById('progressBar');
        this.progressMessage = document.getElementById('progressMessage');
        this.stepsContainer = document.getElementById('stepsContainer');
        
        // Result elements
        this.monacoEditor = document.getElementById('monacoEditor');
        this.saveCodeBtn = document.getElementById('saveCodeBtn');
        this.copyCodeBtn = document.getElementById('copyCodeBtn');
        this.downloadCodeBtn = document.getElementById('downloadCodeBtn');
        
        // Monaco Editor state
        this.editor = null;
        this.hasChanges = false;
        this.currentFilePath = null;
        this.stepDetails = {}; // Store details for each step
        
        // Metadata elements
        this.metaMappingName = document.getElementById('metaMappingName');
        this.metaProjectName = document.getElementById('metaProjectName');
        this.metaTimestamp = document.getElementById('metaTimestamp');
        this.metaTableCount = document.getElementById('metaTableCount');
        this.metaHadExisting = document.getElementById('metaHadExisting');
        this.metaStatus = document.getElementById('metaStatus');
        
        // Error elements
        this.errorMessage = document.getElementById('errorMessage');
        
        // Define generation steps
        this.steps = [
            { id: 'extraction', title: 'Extracting Mapping Info', description: 'Analyzing prompt to extract mapping name and version', detailsKey: 'prompt_extraction' },
            { id: 'mapping', title: 'Fetching Mapping Details', description: 'Retrieving mapping configuration from MCP server', detailsKey: 'mapping_details' },
            { id: 'tables', title: 'Extracting Table Names', description: 'Analyzing mapping to identify required tables', detailsKey: 'table_names' },
            { id: 'structures', title: 'Fetching Table Structures', description: 'Getting column information for all tables', detailsKey: 'table_structures' },
            { id: 'existing', title: 'Checking Existing Code', description: 'Looking for any previously generated code', detailsKey: 'existing_code' },
            { id: 'llm_prompt', title: 'LLM Prompt', description: 'Prompt sent to AI model for code generation', detailsKey: 'llm_prompt' },
            { id: 'llm', title: 'Generating Code with AI', description: 'Using LLM to generate optimized SQL code', detailsKey: 'llm_response' },
            { id: 'save', title: 'Saving Generated Code', description: 'Writing code to file system', detailsKey: 'save_result' }
        ];
    }
    
    attachEventListeners() {
        // Form submission
        document.getElementById('codeGenForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.startGeneration();
        });
        
        // Reset button
        this.resetBtn.addEventListener('click', () => {
            this.resetForm();
        });
        
        // Refresh button
        this.refreshBtn.addEventListener('click', () => {
            this.loadProjects();
        });
        
        // Copy button
        this.copyCodeBtn.addEventListener('click', () => {
            this.copyCode();
        });
        
        // Download button
        this.downloadCodeBtn.addEventListener('click', () => {
            this.downloadCode();
        });
        
        // Save code button
        this.saveCodeBtn.addEventListener('click', () => {
            this.saveCode();
        });
    }
    
    showLoading(show = true) {
        if (show) {
            this.loadingSpinner.classList.remove('d-none');
        } else {
            this.loadingSpinner.classList.add('d-none');
        }
    }
    
    showError(message, keepProgress = false) {
        if (!keepProgress) {
            // Show error in error card only when not keeping progress
            this.errorMessage.textContent = message;
            this.errorCard.classList.remove('d-none');
            this.resultsCard.classList.add('d-none');
            this.progressCard.classList.add('d-none');
        } else {
            // Keep progress card visible and only show error below progress bar
            this.progressMessage.innerHTML = `<span class="text-danger"><i class="fas fa-exclamation-triangle me-2"></i>${message}</span>`;
            // Keep errorCard hidden
            this.errorCard.classList.add('d-none');
        }
    }
    
    hideError() {
        this.errorCard.classList.add('d-none');
    }
    
    async loadProjects() {
        try {
            this.showLoading(true);
            
            const response = await fetch('/code-generator/api/projects');
            const data = await response.json();
            
            if (data.success) {
                this.populateProjectSelect(data.projects);
            } else {
                this.showError(data.error || 'Failed to load projects');
            }
        } catch (error) {
            console.error('Error loading projects:', error);
            this.showError('Failed to load projects: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    populateProjectSelect(projects) {
        this.projectSelect.innerHTML = '<option value="">-- Select Project --</option>';
        
        projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.name;
            option.textContent = project.name;
            option.dataset.projectId = project.id;
            this.projectSelect.appendChild(option);
        });
    }
    
    async startGeneration() {
        const projectName = this.projectSelect.value;
        const userPrompt = this.userPrompt.value.trim();
        
        if (!projectName) {
            this.showError('Please select a project', false);
            return;
        }
        
        if (!userPrompt) {
            this.showError('Please enter a prompt', false);
            return;
        }
        
        try {
            // Hide previous results and clear any previous result UI
            this.hideError();
            this.resultsCard.classList.add('d-none');

            // Clear previous results steps (from prior runs) so final display doesn't accumulate old steps
            const stepsContainerResultsClear = document.getElementById('stepsContainerResults');
            if (stepsContainerResultsClear) stepsContainerResultsClear.innerHTML = '';

            // Dispose any existing Monaco editor from previous run to avoid stale content
            if (this.editor) {
                try {
                    this.editor.dispose();
                } catch (e) {
                    console.warn('Error disposing previous editor:', e);
                }
                this.editor = null;
            }
            this.currentFilePath = null;
            this.stepDetails = {};
            
            // Show progress card and initialize steps
            this.progressCard.classList.remove('d-none');
            this.updateProgress(0, 'Initializing code generation...');
            this.initializeSteps();
            
            // Disable form
            this.generateBtn.disabled = true;
            this.projectSelect.disabled = true;
            this.userPrompt.disabled = true;
            
            // Start generation
            const response = await fetch('/code-generator/api/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_prompt: userPrompt,
                    project_name: projectName
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentOperationId = data.operation_id;
                this.startProgressPolling();
            } else {
                this.showError(data.error || 'Failed to start code generation', false);
                this.enableForm();
            }
        } catch (error) {
            console.error('Error starting generation:', error);
            this.showError('Failed to start code generation: ' + error.message, false);
            this.enableForm();
        }
    }
    
    initializeSteps() {
        // Clear previous steps and details
        this.stepsContainer.innerHTML = '';
        this.stepDetails = {};
        
        // Add all steps as pending
        this.steps.forEach((step, index) => {
            const stepElement = document.createElement('div');
            stepElement.className = 'step-item pending';
            stepElement.id = `step-${index}`;
            stepElement.innerHTML = `
                <div class="step-number">${index + 1}</div>
                <div class="step-content">
                    <h6>
                        <span>${step.title}</span>
                        <span class="step-toggle-icon">▶</span>
                    </h6>
                    <div class="step-description">${step.description}</div>
                    <div class="step-details" id="step-details-${index}"></div>
                </div>
            `;
            
            // Add click handler for collapse/expand
            const header = stepElement.querySelector('h6');
            header.addEventListener('click', () => {
                this.toggleStepDetails(index);
            });
            
            this.stepsContainer.appendChild(stepElement);
        });
    }
    
    toggleStepDetails(stepIndex) {
        const detailsDiv = document.getElementById(`step-details-${stepIndex}`);
        const toggleIcon = document.querySelector(`#step-${stepIndex} .step-toggle-icon`);
        
        if (detailsDiv.classList.contains('show')) {
            detailsDiv.classList.remove('show');
            toggleIcon.classList.remove('expanded');
        } else {
            detailsDiv.classList.add('show');
            toggleIcon.classList.add('expanded');
        }
    }
    
    updateStepDetails(stepIndex, details) {
        const detailsDiv = document.getElementById(`step-details-${stepIndex}`);
        if (!detailsDiv) return;
        
        let content = '';
        if (typeof details === 'object') {
            content = `<pre>${JSON.stringify(details, null, 2)}</pre>`;
        } else if (typeof details === 'string') {
            content = `<pre>${details}</pre>`;
        }
        
        detailsDiv.innerHTML = content;
        
        // Store details
        this.stepDetails[stepIndex] = details;
    }
    
    markCurrentStepAsError(errorMessage) {
        // Find the current step (last one that's not pending)
        const steps = document.querySelectorAll('.step-item');
        let currentStep = null;
        
        for (let i = steps.length - 1; i >= 0; i--) {
            if (steps[i].classList.contains('current') || steps[i].classList.contains('completed')) {
                currentStep = steps[i];
                break;
            }
        }
        
        if (currentStep) {
            currentStep.classList.remove('current', 'pending', 'completed');
            currentStep.classList.add('error');
            
            // Don't replace step details - just mark the step visually as error
            // The error message is shown below the progress bar
        }
    }
    
    updateStepStatus(message) {
        // Map progress messages to step indices
        const stepMapping = {
            'Extracting mapping info from prompt': 0,
            'Fetching mapping details': 1,
            'Extracting table names': 2,
            'Fetching table structures': 3,
            'Checking for existing code': 4,
            'Prompt sent to LLM': 5,
            'Generating code with AI': 6,
            'Saving generated code': 7
        };
        
        // Find which step we're on
        for (const [keyword, stepIndex] of Object.entries(stepMapping)) {
            if (message.toLowerCase().includes(keyword.toLowerCase())) {
                // Mark previous steps as completed
                for (let i = 0; i < stepIndex; i++) {
                    const stepEl = document.getElementById(`step-${i}`);
                    if (stepEl) {
                        stepEl.classList.remove('pending', 'current');
                        stepEl.classList.add('completed');
                    }
                }
                
                // Mark current step as current
                const currentStepEl = document.getElementById(`step-${stepIndex}`);
                if (currentStepEl) {
                    currentStepEl.classList.remove('pending');
                    currentStepEl.classList.add('current');
                }
                
                break;
            }
        }
    }
    
    completeAllSteps() {
        // Mark all steps as completed
        this.steps.forEach((_, index) => {
            const stepEl = document.getElementById(`step-${index}`);
            if (stepEl) {
                stepEl.classList.remove('pending', 'current');
                stepEl.classList.add('completed');
            }
        });
    }
    
    startProgressPolling() {
        // Poll every 500ms
        this.progressInterval = setInterval(() => {
            this.checkProgress();
        }, 500);
    }
    
    stopProgressPolling() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    }
    
    async checkProgress() {
        if (!this.currentOperationId) return;
        
        try {
            const response = await fetch(`/code-generator/api/progress/${this.currentOperationId}`);
            const data = await response.json();
            
            if (!data.success) {
                this.stopProgressPolling();
                this.markCurrentStepAsError(data.error || 'Failed to check progress');
                this.showError(data.error || 'Failed to check progress', true);
                this.enableForm();
                return;
            }
            
            // Update progress
            this.updateProgress(data.progress, data.message);
            
            // Update step details if available
            if (data.step_details) {
                this.updateStepsWithDetails(data.step_details);
            }
            
            // Check status
            if (data.status === 'completed') {
                this.stopProgressPolling();
                this.showResults(data.result);
                this.enableForm();
                
                // Cleanup operation from server
                this.cleanupOperation(this.currentOperationId);
                this.currentOperationId = null;
                
            } else if (data.status === 'error') {
                this.stopProgressPolling();
                
                // Mark current step as error
                this.markCurrentStepAsError(data.error || 'Code generation failed');
                
                // Show error but keep progress visible
                this.showError(data.error || 'Code generation failed', true);
                this.enableForm();
                
                // Cleanup operation from server
                this.cleanupOperation(this.currentOperationId);
                this.currentOperationId = null;
            }
        } catch (error) {
            console.error('Error checking progress:', error);
            this.stopProgressPolling();
            this.markCurrentStepAsError('Failed to check progress: ' + error.message);
            this.showError('Failed to check progress: ' + error.message, true);
            this.enableForm();
        }
    }
    
    updateStepsWithDetails(stepDetails) {
        // Map step keys to step indices
        const keyToIndex = {
            'prompt_extraction': 0,
            'mapping_details': 1,
            'table_names': 2,
            'table_structures': 3,
            'existing_code': 4,
            'llm_prompt': 5,
            'llm_response': 6,
            'save_result': 7
        };
        
        // Update details for each available step
        for (const [key, details] of Object.entries(stepDetails)) {
            const stepIndex = keyToIndex[key];
            if (stepIndex !== undefined && details) {
                this.updateStepDetails(stepIndex, details);
            }
        }
    }
    
    updateProgress(percentage, message) {
        this.progressBar.style.width = percentage + '%';
        this.progressBar.textContent = percentage + '%';
        this.progressMessage.textContent = message;
        
        // Update step status based on message
        this.updateStepStatus(message);
    }
    
    showResults(result) {
        // Move steps from progress card to results card
        const stepsContainer = document.getElementById('stepsContainer');
        const stepsContainerResults = document.getElementById('stepsContainerResults');

        // Ensure previous results are cleared before appending new ones
        if (stepsContainerResults) {
            stepsContainerResults.innerHTML = '';
        }

        // Move all step elements from progress to results container
        while (stepsContainer && stepsContainer.firstChild) {
            if (stepsContainerResults) {
                stepsContainerResults.appendChild(stepsContainer.firstChild);
            } else {
                // If results container is missing, just remove from progress
                stepsContainer.removeChild(stepsContainer.firstChild);
            }
        }
        
        // Hide progress card
        this.progressCard.classList.add('d-none');
        
        // Show results card
        this.resultsCard.classList.remove('d-none');
        
        // Complete all steps
        this.completeAllSteps();
        
        // Update step details with result data (only if not already populated)
        if (result.mapping_details && !this.stepDetails[0]) {
            this.updateStepDetails(0, result.mapping_details);
        }
        if (result.table_names && !this.stepDetails[1]) {
            this.updateStepDetails(1, { tables: result.table_names });
        }
        if (result.table_structures && !this.stepDetails[2]) {
            this.updateStepDetails(2, result.table_structures);
        }
        if (result.existing_code && !this.stepDetails[3]) {
            this.updateStepDetails(3, result.existing_code);
        }
        if (result.llm_response && !this.stepDetails[4]) {
            this.updateStepDetails(4, result.llm_response);
        }
        if (result.file_path && !this.stepDetails[5]) {
            this.updateStepDetails(5, { file_path: result.file_path, status: 'saved' });
        }
        
        // Update metadata
        this.metaMappingName.textContent = result.mapping_name || '-';
        this.metaProjectName.textContent = result.project_name || '-';
        
        const timestamp = result.timestamp ? new Date(result.timestamp).toLocaleString() : '-';
        this.metaTimestamp.textContent = timestamp;
        
        const tableCount = result.table_names ? result.table_names.length : 0;
        this.metaTableCount.textContent = tableCount;
        
        this.metaHadExisting.textContent = result.had_existing_code ? 'Yes' : 'No';
        
        // Update status badge
        this.metaStatus.textContent = 'Success';
        this.metaStatus.className = 'badge bg-success';
        
        // Store file path for saving
        this.currentFilePath = result.file_path;
        
        // Initialize Monaco Editor
        this.initializeMonacoEditor(result.code || '');
    }
    
    initializeMonacoEditor(code) {
        // Check if monaco is loaded via the loader
        if (typeof require === 'undefined' || typeof require.config === 'undefined') {
            console.error('Monaco Editor loader not available');
            // Fallback: show code in a div
            this.monacoEditor.innerHTML = `<pre style="padding: 1rem; background: #1e1e1e; color: #d4d4d4; overflow: auto; height: 500px;">${code}</pre>`;
            return;
        }
        
        // Configure Monaco loader for CDN version
        require.config({ 
            paths: { 'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' }
        });
        
        // Detect current theme
        const isDarkTheme = !document.body.classList.contains('theme-light') && 
                           !document.body.classList.contains('theme-lightColored');
        const editorTheme = isDarkTheme ? 'vs-dark' : 'vs';
        
        // Load Monaco Editor
        require(['vs/editor/editor.main'], () => {
            // Dispose existing editor
            if (this.editor) {
                this.editor.dispose();
            }
            
            // Create Monaco Editor with SQL language
            this.editor = monaco.editor.create(this.monacoEditor, {
                value: code,
                language: 'sql',
                theme: editorTheme,
                automaticLayout: true,
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                wordWrap: 'on',
                readOnly: false,
                renderWhitespace: 'selection',
                folding: true,
                lineDecorationsWidth: 10,
                lineNumbersMinChars: 3
            });
            
            // Force language to SQL to ensure syntax highlighting
            if (this.editor.getModel()) {
                monaco.editor.setModelLanguage(this.editor.getModel(), 'sql');
            }
            
            // Track changes
            this.hasChanges = false;
            this.editor.onDidChangeModelContent(() => {
                this.hasChanges = true;
                this.saveCodeBtn.classList.remove('d-none');
            });
        });
    }
    
    async saveCode() {
        if (!this.editor || !this.currentFilePath) {
            this.showError('No file to save');
            return;
        }
        
        try {
            const code = this.editor.getValue();
            
            const response = await fetch('/code-generator/api/save-code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file: this.currentFilePath,  // Changed from file_path to file
                    code: code
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.hasChanges = false;
                this.saveCodeBtn.classList.add('d-none');
                
                // Show success message
                const originalHTML = this.saveCodeBtn.innerHTML;
                this.saveCodeBtn.innerHTML = '<i class="bi bi-check-circle me-1"></i>Saved!';
                this.saveCodeBtn.classList.remove('d-none');
                this.saveCodeBtn.classList.add('btn-outline-success');
                this.saveCodeBtn.classList.remove('btn-success');
                
                setTimeout(() => {
                    this.saveCodeBtn.innerHTML = originalHTML;
                    this.saveCodeBtn.classList.add('d-none');
                    this.saveCodeBtn.classList.remove('btn-outline-success');
                    this.saveCodeBtn.classList.add('btn-success');
                }, 2000);
            } else {
                this.showError(data.error || 'Failed to save code');
            }
        } catch (error) {
            console.error('Error saving code:', error);
            this.showError('Failed to save code: ' + error.message);
        }
    }
    
    enableForm() {
        this.generateBtn.disabled = false;
        this.projectSelect.disabled = false;
        this.userPrompt.disabled = false;
    }
    
    resetForm() {
        // Stop any active polling
        this.stopProgressPolling();
        
        // Reset form
        this.projectSelect.value = '';
        this.userPrompt.value = '';
        
        // Hide cards
        this.progressCard.classList.add('d-none');
        this.resultsCard.classList.add('d-none');
        this.errorCard.classList.add('d-none');
        
        // Clear steps from both containers
        const stepsContainer = document.getElementById('stepsContainer');
        const stepsContainerResults = document.getElementById('stepsContainerResults');
        if (stepsContainer) stepsContainer.innerHTML = '';
        if (stepsContainerResults) stepsContainerResults.innerHTML = '';
        
        // Dispose Monaco Editor
        if (this.editor) {
            this.editor.dispose();
            this.editor = null;
        }
        
        // Reset editor state
        this.hasChanges = false;
        this.currentFilePath = null;
        this.stepDetails = {};
        this.saveCodeBtn.classList.add('d-none');
        
        // Enable form
        this.enableForm();
        
        // Clear current operation
        if (this.currentOperationId) {
            this.cleanupOperation(this.currentOperationId);
            this.currentOperationId = null;
        }
    }
    
    async cleanupOperation(operationId) {
        try {
            await fetch(`/code-generator/api/cleanup/${operationId}`, {
                method: 'DELETE'
            });
        } catch (error) {
            console.error('Error cleaning up operation:', error);
        }
    }
    
    copyCode() {
        if (!this.editor) {
            alert('No code to copy');
            return;
        }
        
        const code = this.editor.getValue();
        
        if (!code) {
            alert('No code to copy');
            return;
        }
        
        navigator.clipboard.writeText(code).then(() => {
            // Show success feedback
            const originalText = this.copyCodeBtn.innerHTML;
            this.copyCodeBtn.innerHTML = '<i class="fas fa-check"></i> Copied!';
            this.copyCodeBtn.classList.add('btn-success');
            this.copyCodeBtn.classList.remove('btn-outline-light');
            
            setTimeout(() => {
                this.copyCodeBtn.innerHTML = originalText;
                this.copyCodeBtn.classList.remove('btn-success');
                this.copyCodeBtn.classList.add('btn-outline-light');
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy code:', err);
            alert('Failed to copy code to clipboard');
        });
    }
    
    downloadCode() {
        if (!this.editor) {
            alert('No code to download');
            return;
        }
        
        const code = this.editor.getValue();
        const mappingName = this.metaMappingName.textContent;
        
        if (!code) {
            alert('No code to download');
            return;
        }
        
        // Create blob and download
        const blob = new Blob([code], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${mappingName.replace(/\s+/g, '_')}.sql`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }
}
