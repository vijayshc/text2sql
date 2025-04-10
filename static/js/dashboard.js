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
        
        // Get the data
        if (!text2sql.currentResult || 
            !text2sql.currentResult.chart_data || 
            !text2sql.currentResult.chart_data.data) {
            uiUtils.showToast('No query data available for charting', 'warning');
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
        
        // Create the chart
        this.createChart(chartType, xData, yData, chartTitle, xAxisLabel, yAxisLabel);
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
        
        // Show canvas, hide message
        $('#dashboardChart').show();
        $('#noChartMessage').hide();
        
        // Configure the chart options based on chart type
        const options = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: title,
                    font: {
                        size: 14
                    }
                },
                legend: {
                    display: chartType === 'pie' || chartType === 'doughnut',
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 10,
                        font: {
                            size: 14
                        }
                    }
                }
            }
        };
        
        // Add scales for chart types that support them
        if (chartType !== 'pie' && chartType !== 'doughnut') {
            options.scales = {
                x: {
                    title: {
                        display: true,
                        text: xLabel,
                        font: {
                            size: 14
                        }
                    },
                    ticks: {
                        font: {
                            size: 14
                        }
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: yLabel,
                        font: {
                            size: 14
                        }
                    },
                    ticks: {
                        font: {
                            size: 14
                        }
                    }
                }
            };
        }
        
        // Configure the chart data
        let chartData;
        
        // Different configuration based on chart type
        if (chartType === 'pie' || chartType === 'doughnut') {
            // Generate a color palette
            const backgroundColors = this.generateColorPalette(xData.length);
            
            chartData = {
                labels: xData,
                datasets: [{
                    label: yLabel,
                    data: yData,
                    backgroundColor: backgroundColors
                }]
            };
        } else {
            chartData = {
                labels: xData,
                datasets: [{
                    label: yLabel,
                    data: yData,
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgb(54, 162, 235)',
                    borderWidth: 1
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
     * Generate a color palette for chart elements
     */
    generateColorPalette: function(count) {
        const baseColors = [
            'rgba(255, 99, 132, 0.7)',   // Red
            'rgba(54, 162, 235, 0.7)',   // Blue
            'rgba(255, 206, 86, 0.7)',   // Yellow
            'rgba(75, 192, 192, 0.7)',   // Green
            'rgba(153, 102, 255, 0.7)',  // Purple
            'rgba(255, 159, 64, 0.7)',   // Orange
            'rgba(199, 199, 199, 0.7)',  // Gray
            'rgba(83, 102, 255, 0.7)',   // Indigo
            'rgba(255, 99, 255, 0.7)',   // Pink
            'rgba(159, 159, 64, 0.7)',   // Olive
        ];
        
        // If we need more colors than we have in baseColors, generate them
        const colors = [...baseColors];
        
        if (count > baseColors.length) {
            for (let i = baseColors.length; i < count; i++) {
                // Generate random colors for additional items
                const r = Math.floor(Math.random() * 255);
                const g = Math.floor(Math.random() * 255);
                const b = Math.floor(Math.random() * 255);
                colors.push(`rgba(${r}, ${g}, ${b}, 0.7)`);
            }
        }
        
        return colors.slice(0, count);
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
                // Prepare the dashboard but don't switch tabs
                console.log('Automatic dashboard created successfully');
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
