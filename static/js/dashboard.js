/**
 * dashboard.js - Dashboard visualization functionality using Chart.js
 */

const dashboard = {
    currentChart: null,
    chartData: null,
    
    /**
     * Initialize the dashboard
     */
    init: function() {
        // Set up event listeners
        this.setupEventListeners();
        
        // Hide the chart initially and show message
        $('#dashboardChart').hide();
        $('#noChartMessage').show();
        
        // Check if Chart.js is loaded
        if (typeof Chart === 'undefined') {
            console.error('Chart.js is not loaded. Dashboard visualization will not work.');
            uiUtils.showToast('Chart.js library not loaded. Dashboard visualization may not work correctly.', 'error');
        }
    },
    
    /**
     * Setup event listeners for dashboard controls
     */
    setupEventListeners: function() {
        // Generate chart button click
        $('#generateChartBtn').on('click', () => this.generateChart());
        
        // Chart type change - show/hide relevant options
        $('#chartType').on('change', () => this.updateChartOptions());
        
        // Dashboard tab shown event
        $('a[href="#dashboard"]').on('shown.bs.tab', () => {
            this.populateAxisDropdowns();
            // Refresh chart if it exists (fixes chart resize issues)
            if (this.currentChart) {
                setTimeout(() => {
                    this.currentChart.resize();
                }, 10);
            }
        });
    },
    
    /**
     * Populate the axis dropdowns with column names from result data
     */
    populateAxisDropdowns: function() {
        // Clear existing options except the first one
        $('#chartXAxis option:not(:first)').remove();
        $('#chartYAxis option:not(:first)').remove();
        
        // Get columns from the result data
        const columns = this.getAvailableColumns();
        if (!columns || columns.length === 0) {
            console.log('No columns available for charting');
            return;
        }
        
        // Add options to each dropdown
        columns.forEach(column => {
            $('#chartXAxis').append(`<option value="${column}">${column}</option>`);
            $('#chartYAxis').append(`<option value="${column}">${column}</option>`);
        });
    },
    
    /**
     * Get available columns from current result data
     */
    getAvailableColumns: function() {
        // If we have chart data in text2sql.currentResult
        if (text2sql.currentResult && 
            text2sql.currentResult.chart_data && 
            text2sql.currentResult.chart_data.columns) {
            return text2sql.currentResult.chart_data.columns;
        }
        return [];
    },
    
    /**
     * Update chart options based on selected chart type
     */
    updateChartOptions: function() {
        const chartType = $('#chartType').val();
        
        // Show/hide axis inputs based on chart type
        if (chartType === 'pie' || chartType === 'doughnut') {
            $('#chartYAxisLabel').closest('.col-md-4').hide();
            $('#chartXAxisLabel').closest('.col-md-4').hide();
        } else {
            $('#chartYAxisLabel').closest('.col-md-4').show();
            $('#chartXAxisLabel').closest('.col-md-4').show();
        }
    },
    
    /**
     * Generate a chart based on the form inputs
     */
    generateChart: function() {
        // Get form values
        const chartType = $('#chartType').val();
        const xAxisColumn = $('#chartXAxis').val();
        const yAxisColumn = $('#chartYAxis').val();
        const chartTitle = $('#chartTitle').val() || 'Data Visualization';
        const xAxisLabel = $('#chartXAxisLabel').val() || xAxisColumn;
        const yAxisLabel = $('#chartYAxisLabel').val() || yAxisColumn;
        
        // Validate inputs
        if (!xAxisColumn || !yAxisColumn) {
            uiUtils.showToast('Please select both X and Y axis columns', 'warning');
            return;
        }
        
        // Show loading state
        const btn = $('#generateChartBtn');
        const originalText = btn.text();
        btn.addClass('loading').prop('disabled', true);
        
        // Get the data
        if (!text2sql.currentResult || 
            !text2sql.currentResult.chart_data || 
            !text2sql.currentResult.chart_data.data) {
            uiUtils.showToast('No query data available for charting', 'warning');
            btn.removeClass('loading').prop('disabled', false);
            return;
        }
        
        // Extract data for the selected columns
        const rawData = text2sql.currentResult.chart_data.data;
        const xData = [];
        const yData = [];
        
        rawData.forEach(row => {
            xData.push(row[xAxisColumn]);
            yData.push(row[yAxisColumn]);
        });
        
        // Create the chart with a slight delay for better UX
        setTimeout(() => {
            this.createChart(chartType, xData, yData, chartTitle, xAxisLabel, yAxisLabel);
            btn.removeClass('loading').prop('disabled', false);
        }, 300);
    },
    
    /**
     * Create a chart with the given configuration
     */
    createChart: function(chartType, xData, yData, title, xLabel, yLabel) {
        // Check if Chart.js is available
        if (typeof Chart === 'undefined') {
            uiUtils.showToast('Chart.js library is not available. Unable to create chart.', 'error');
            console.error('Chart.js is not defined. Cannot create chart.');
            return;
        }
        
        // Destroy existing chart if it exists
        if (this.currentChart) {
            this.currentChart.destroy();
        }
        
        // Get the canvas element
        const canvas = document.getElementById('dashboardChart');
        const ctx = canvas.getContext('2d');
        
        // Show canvas, hide message with animation
        $('#noChartMessage').fadeOut(200, function() {
            $('#dashboardChart').fadeIn(300);
        });
        
        // Configure the chart options based on chart type with dark theme styling
        const options = {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: 1000,
                easing: 'easeInOutQuart'
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                title: {
                    display: true,
                    text: title,
                    color: '#ffffff',
                    font: {
                        size: 16,
                        weight: '500'
                    },
                    padding: {
                        top: 10,
                        bottom: 20
                    }
                },
                legend: {
                    display: chartType === 'pie' || chartType === 'doughnut',
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 15,
                        color: '#e5e5e5',
                        font: {
                            size: 13
                        },
                        usePointStyle: true
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(31, 31, 31, 0.95)',
                    titleColor: '#ffffff',
                    bodyColor: '#e5e5e5',
                    borderColor: '#2d2d2d',
                    borderWidth: 1,
                    cornerRadius: 6,
                    displayColors: true,
                    padding: 12
                }
            }
        };
        
        // Add scales for chart types that support them with dark theme styling
        if (chartType !== 'pie' && chartType !== 'doughnut') {
            options.scales = {
                x: {
                    title: {
                        display: true,
                        text: xLabel,
                        color: '#e5e5e5',
                        font: {
                            size: 13,
                            weight: '500'
                        }
                    },
                    ticks: {
                        color: '#b0b0b0',
                        font: {
                            size: 12
                        }
                    },
                    grid: {
                        color: 'rgba(176, 176, 176, 0.2)',
                        lineWidth: 1
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: yLabel,
                        color: '#e5e5e5',
                        font: {
                            size: 13,
                            weight: '500'
                        }
                    },
                    ticks: {
                        color: '#b0b0b0',
                        font: {
                            size: 12
                        }
                    },
                    grid: {
                        color: 'rgba(176, 176, 176, 0.2)',
                        lineWidth: 1
                    }
                }
            };
        }
        
        // Configure the chart data with improved dark theme colors
        let chartData;
        
        // Different configuration based on chart type
        if (chartType === 'pie' || chartType === 'doughnut') {
            // Generate a color palette for pie/doughnut charts
            const colorPalette = this.generateColorPalette(xData.length);
            
            chartData = {
                labels: xData,
                datasets: [{
                    label: yLabel,
                    data: yData,
                    backgroundColor: colorPalette.backgrounds,
                    borderColor: colorPalette.borders,
                    borderWidth: 2,
                    hoverBorderWidth: 3,
                    hoverOffset: 6,
                    hoverBorderColor: '#ffffff'
                }]
            };
        } else {
            // For bar, line charts, use a consistent color scheme
            const colorPalette = this.generateColorPalette(1);
            
            chartData = {
                labels: xData,
                datasets: [{
                    label: yLabel,
                    data: yData,
                    backgroundColor: colorPalette.backgrounds[0],
                    borderColor: colorPalette.borders[0],
                    borderWidth: 2,
                    pointBackgroundColor: colorPalette.borders[0],
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: chartType === 'line' ? 4 : 0,
                    pointHoverRadius: chartType === 'line' ? 6 : 0,
                    pointHoverBorderWidth: chartType === 'line' ? 3 : 0,
                    tension: chartType === 'line' ? 0.3 : 0,
                    hoverBackgroundColor: colorPalette.borders[0],
                    hoverBorderColor: '#ffffff',
                    hoverBorderWidth: 3
                }]
            };
        }
        
        // Create the chart
        this.currentChart = new Chart(ctx, {
            type: chartType,
            data: chartData,
            options: options
        });
        
        // Add success message
        uiUtils.showToast('Chart generated successfully', 'success');
    },
    
    /**
     * Generate a color palette for chart elements optimized for dark theme
     */
    generateColorPalette: function(count) {
        const baseColors = [
            'rgba(56, 189, 248, 0.8)',   // Bright Sky Blue
            'rgba(34, 197, 94, 0.8)',    // Bright Green
            'rgba(251, 146, 60, 0.8)',   // Bright Orange
            'rgba(168, 85, 247, 0.8)',   // Bright Purple
            'rgba(244, 63, 94, 0.8)',    // Bright Pink
            'rgba(245, 158, 11, 0.8)',   // Bright Amber
            'rgba(20, 184, 166, 0.8)',   // Bright Teal
            'rgba(99, 102, 241, 0.8)',   // Bright Indigo
            'rgba(236, 72, 153, 0.8)',   // Bright Rose
            'rgba(132, 204, 22, 0.8)',   // Bright Lime
            'rgba(6, 182, 212, 0.8)',    // Bright Cyan
            'rgba(139, 69, 19, 0.8)',    // Brown
        ];
        
        // Border colors with higher opacity for better visibility
        const borderColors = [
            'rgba(56, 189, 248, 1)',     // Sky Blue border
            'rgba(34, 197, 94, 1)',      // Green border
            'rgba(251, 146, 60, 1)',     // Orange border
            'rgba(168, 85, 247, 1)',     // Purple border
            'rgba(244, 63, 94, 1)',      // Pink border
            'rgba(245, 158, 11, 1)',     // Amber border
            'rgba(20, 184, 166, 1)',     // Teal border
            'rgba(99, 102, 241, 1)',     // Indigo border
            'rgba(236, 72, 153, 1)',     // Rose border
            'rgba(132, 204, 22, 1)',     // Lime border
            'rgba(6, 182, 212, 1)',      // Cyan border
            'rgba(139, 69, 19, 1)',      // Brown border
        ];
        
        // If we need more colors than we have in baseColors, generate them with better visibility
        const colors = [...baseColors];
        const borders = [...borderColors];
        
        if (count > baseColors.length) {
            for (let i = baseColors.length; i < count; i++) {
                // Generate bright, saturated colors for dark theme
                const hue = (i * 137.5) % 360; // Golden angle for even distribution
                const saturation = 70 + (i % 3) * 10; // 70-90% saturation
                const lightness = 55 + (i % 2) * 10; // 55-65% lightness
                colors.push(`hsla(${hue}, ${saturation}%, ${lightness}%, 0.8)`);
                borders.push(`hsla(${hue}, ${saturation}%, ${lightness}%, 1)`);
            }
        }
        
        return {
            backgrounds: colors.slice(0, count),
            borders: borders.slice(0, count)
        };
    },
    
    /**
     * Handle new query results - prepare for dashboard
     */
    handleQueryResults: function(result) {
        // Reset chart if there's no data
        if (!result || !result.chart_data || !result.chart_data.data) {
            if (this.currentChart) {
                this.currentChart.destroy();
                this.currentChart = null;
            }
            $('#dashboardChart').hide();
            $('#noChartMessage').show();
            return;
        }
        
        // Store the result for later use
        this.chartData = result.chart_data;
        
        // Check if we have dashboard recommendations from AI
        const hasRecommendations = result.chart_data.dashboard_recommendations && 
                                 result.chart_data.dashboard_recommendations.is_suitable === true;
        
        // If we have dashboard recommendations, prepare the chart but don't switch tabs
        if (hasRecommendations) {
            console.log('Creating automatic dashboard based on AI recommendations');
            
            // Create automatic dashboard without switching to the tab
            if (this.createAutomaticDashboard(result.chart_data.dashboard_recommendations)) {
                console.log('Automatic dashboard created successfully');
                // Show success indicator
                uiUtils.showToast('Smart chart visualization ready! Check the Dashboard tab.', 'info');
            } else {
                console.warn('Failed to create automatic dashboard from recommendations');
            }
        }
        
        // Always populate the dropdowns regardless of whether we automatically created a chart
        this.populateAxisDropdowns();
    },

    /**
     * Create a chart automatically based on AI recommendations
     */
    createAutomaticDashboard: function(recommendations) {
        if (!recommendations || !recommendations.is_suitable) {
            return false;
        }
        
        try {
            // Get recommendations
            const chartType = recommendations.chart_type.toLowerCase();
            const xAxis = recommendations.x_axis.column;
            const yAxis = recommendations.y_axis.column;
            const title = recommendations.title;
            const xLabel = recommendations.x_axis.label;
            const yLabel = recommendations.y_axis.label;
            
            // Validate that we have the necessary data
            if (!chartType || !xAxis || !yAxis) {
                console.warn('Incomplete dashboard recommendations', recommendations);
                return false;
            }
            
            // Map recommended chart type to Chart.js type
            let chartJsType = chartType;
            if (chartType.includes('bar')) {
                chartJsType = 'bar';
            } else if (chartType.includes('line')) {
                chartJsType = 'line';
            } else if (chartType.includes('pie')) {
                chartJsType = 'pie';
            } else if (chartType.includes('scatter')) {
                chartJsType = 'scatter';
            } else if (chartType.includes('doughnut')) {
                chartJsType = 'doughnut';
            }
            
            // Get the data from current result
            const rawData = text2sql.currentResult.chart_data.data;
            const xData = [];
            const yData = [];
            
            rawData.forEach(row => {
                xData.push(row[xAxis]);
                yData.push(row[yAxis]);
            });
            
            // Create the chart
            this.createChart(chartJsType, xData, yData, title, xLabel, yLabel);
            
            // Show a toast notification about the automatic chart
            uiUtils.showToast('Dashboard automatically created based on query analysis', 'info');
            
            // For usability, update the form fields to match what was automatically selected
            $('#chartType').val(chartJsType);
            $('#chartXAxis').val(xAxis);
            $('#chartYAxis').val(yAxis);
            $('#chartTitle').val(title);
            $('#chartXAxisLabel').val(xLabel);
            $('#chartYAxisLabel').val(yLabel);
            
            // Update any dependent UI elements
            this.updateChartOptions();
            
            return true;
        } catch (error) {
            console.error('Error creating automatic dashboard:', error);
            return false;
        }
    },
};

// Initialize dashboard when document is ready
$(document).ready(function() {
    dashboard.init();
});
