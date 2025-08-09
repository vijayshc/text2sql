/**
 * Theme Management System for Text2SQL Application
 * Provides centralized theme switching with session persistence
 */

class ThemeManager {
    constructor() {
        this.themes = {
            dark: {
                name: 'Dark Theme',
                icon: 'fas fa-moon',
                colors: {
                    '--primary-color': '#ffffff',
                    '--secondary-color': '#e5e5e5',
                    '--accent-color': '#b0b0b0',
                    '--success-color': '#10b981',
                    '--warning-color': '#f59e0b',
                    '--danger-color': '#ef4444',
                    '--info-color': '#3b82f6',
                    '--light-bg': '#161616',
                    '--dark-bg': '#1a1a1a',
                    '--card-bg': '#1f1f1f',
                    '--sidebar-bg': '#1a1a1a',
                    '--text-primary': '#ffffff',
                    '--text-secondary': '#b0b0b0',
                    '--text-muted': '#808080',
                    '--border-color': '#2d2d2d',
                    '--hover-bg': '#2a2a2a',
                    '--input-bg': '#2a2a2a',
                    '--input-border': '#3a3a3a',
                    '--input-focus-border': '#4a4a4a',
                    '--table-header-bg': '#2a2a2a',
                    '--table-row-bg': '#1f1f1f',
                    '--table-row-hover': '#2a2a2a',
                    '--table-border': '#3a3a3a',
                    '--button-primary-bg': '#ffffff',
                    '--button-primary-text': '#1f1f1f',
                    '--button-primary-hover': '#e5e5e5',
                    '--button-secondary-bg': '#2a2a2a',
                    '--button-secondary-text': '#ffffff',
                    '--button-secondary-hover': '#3a3a3a',
                    '--card-shadow': '0 2px 8px rgba(0, 0, 0, 0.2)',
                    '--card-shadow-hover': '0 4px 12px rgba(0, 0, 0, 0.3)',
                    '--overlay-bg': 'rgba(0, 0, 0, 0.5)',
                    '--focus-ring': 'rgba(255, 255, 255, 0.1)',
                    '--scrollbar-track': '#2a2a2a',
                    '--scrollbar-thumb': '#4a4a4a',
                    '--syntax-keyword': '#c678dd',
                    '--syntax-string': '#98c379',
                    '--syntax-number': '#d19a66',
                    '--syntax-function': '#61afef',
                    '--syntax-comment': '#5c6370'
                }
            },
            light: {
                name: 'Light Theme',
                icon: 'fas fa-sun',
                colors: {
                    '--primary-color': '#1f2937',
                    '--secondary-color': '#374151',
                    '--accent-color': '#6b7280',
                    '--success-color': '#10b981',
                    '--warning-color': '#f59e0b',
                    '--danger-color': '#ef4444',
                    '--info-color': '#3b82f6',
                    '--light-bg': '#ffffff',
                    '--dark-bg': '#f8fafc',
                    '--card-bg': '#ffffff',
                    '--sidebar-bg': '#f8fafc',
                    '--text-primary': '#1f2937',
                    '--text-secondary': '#374151',
                    '--text-muted': '#6b7280',
                    '--border-color': '#e5e7eb',
                    '--hover-bg': '#f3f4f6',
                    '--input-bg': '#ffffff',
                    '--input-border': '#d1d5db',
                    '--input-focus-border': '#3b82f6',
                    '--table-header-bg': '#f3f4f6',
                    '--table-row-bg': '#ffffff',
                    '--table-row-hover': '#f9fafb',
                    '--table-border': '#e5e7eb',
                    '--button-primary-bg': '#3b82f6',
                    '--button-primary-text': '#ffffff',
                    '--button-primary-hover': '#2563eb',
                    '--button-secondary-bg': '#f3f4f6',
                    '--button-secondary-text': '#374151',
                    '--button-secondary-hover': '#e5e7eb',
                    '--card-shadow': '0 2px 8px rgba(0, 0, 0, 0.1)',
                    '--card-shadow-hover': '0 4px 12px rgba(0, 0, 0, 0.15)',
                    '--overlay-bg': 'rgba(0, 0, 0, 0.3)',
                    '--focus-ring': 'rgba(59, 130, 246, 0.3)',
                    '--scrollbar-track': '#f3f4f6',
                    '--scrollbar-thumb': '#d1d5db',
                    '--syntax-keyword': '#7c3aed',
                    '--syntax-string': '#059669',
                    '--syntax-number': '#dc2626',
                    '--syntax-function': '#2563eb',
                    '--syntax-comment': '#6b7280'
                }
            },
            lightColored: {
                name: 'Light Colored',
                icon: 'fas fa-palette',
                colors: {
                    '--primary-color': '#3b82f6',
                    '--secondary-color': '#1e40af',
                    '--accent-color': '#60a5fa',
                    '--success-color': '#10b981',
                    '--warning-color': '#f59e0b',
                    '--danger-color': '#ef4444',
                    '--info-color': '#3b82f6',
                    '--light-bg': '#ffffff',
                    '--dark-bg': '#f8fafc',
                    '--card-bg': '#ffffff',
                    '--sidebar-bg': '#f0f7ff',
                    '--text-primary': '#1f2937',
                    '--text-secondary': '#374151',
                    '--text-muted': '#6b7280',
                    '--border-color': '#e5e7eb',
                    '--hover-bg': '#f3f4f6',
                    '--input-bg': '#ffffff',
                    '--input-border': '#d1d5db',
                    '--input-focus-border': '#3b82f6',
                    '--table-header-bg': '#f0f7ff',
                    '--table-row-bg': '#ffffff',
                    '--table-row-hover': '#f0f7ff',
                    '--table-border': '#e5e7eb',
                    '--button-primary-bg': '#3b82f6',
                    '--button-primary-text': '#ffffff',
                    '--button-primary-hover': '#2563eb',
                    '--button-secondary-bg': '#f0f7ff',
                    '--button-secondary-text': '#1e40af',
                    '--button-secondary-hover': '#dbeafe',
                    '--card-shadow': '0 2px 8px rgba(59, 130, 246, 0.1)',
                    '--card-shadow-hover': '0 4px 12px rgba(59, 130, 246, 0.15)',
                    '--overlay-bg': 'rgba(0, 0, 0, 0.3)',
                    '--focus-ring': 'rgba(59, 130, 246, 0.3)',
                    '--scrollbar-track': '#f0f7ff',
                    '--scrollbar-thumb': '#bfdbfe',
                    '--syntax-keyword': '#7c3aed',
                    '--syntax-string': '#059669',
                    '--syntax-number': '#dc2626',
                    '--syntax-function': '#2563eb',
                    '--syntax-comment': '#6b7280'
                }
            }
        };
        
        this.currentTheme = this.getStoredTheme() || 'dark';
        this.init();
    }
    
    init() {
        // Apply stored theme on page load
        this.applyTheme(this.currentTheme);
        
        // Listen for theme change events
        document.addEventListener('DOMContentLoaded', () => {
            this.attachEventListeners();
            this.updateThemeSelector();
        });
    }
    
    getStoredTheme() {
        try {
            return sessionStorage.getItem('selectedTheme') || localStorage.getItem('selectedTheme');
        } catch (error) {
            console.warn('Could not access storage for theme:', error);
            return null;
        }
    }
    
    storeTheme(themeName) {
        try {
            // Store in session storage for current session
            sessionStorage.setItem('selectedTheme', themeName);
            // Also store in local storage as fallback
            localStorage.setItem('selectedTheme', themeName);
        } catch (error) {
            console.warn('Could not store theme preference:', error);
        }
    }
    
    applyTheme(themeName) {
        const theme = this.themes[themeName];
        if (!theme) {
            console.warn(`Theme '${themeName}' not found, falling back to dark theme`);
            themeName = 'dark';
            return this.applyTheme(themeName);
        }
        
        const root = document.documentElement;
        
        // Apply CSS custom properties
        Object.entries(theme.colors).forEach(([property, value]) => {
            root.style.setProperty(property, value);
        });
        
        // Update body class for theme-specific styling
        document.body.className = document.body.className.replace(/theme-\w+/g, '');
        document.body.classList.add(`theme-${themeName}`);
        
        // Store the current theme
        this.currentTheme = themeName;
        this.storeTheme(themeName);
        
        // Update the theme selector UI
        this.updateThemeSelector();
        
        // Dispatch custom event for components that need to react to theme changes
        document.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme: themeName, colors: theme.colors }
        }));
        
        console.log(`Applied theme: ${theme.name}`);
    }
    
    switchTheme(themeName) {
        if (this.themes[themeName]) {
            this.applyTheme(themeName);
        }
    }
    
    getAvailableThemes() {
        return Object.keys(this.themes).map(key => ({
            key,
            name: this.themes[key].name,
            icon: this.themes[key].icon,
            current: key === this.currentTheme
        }));
    }
    
    attachEventListeners() {
        // Listen for theme selector clicks
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-theme]') || e.target.closest('[data-theme]')) {
                const themeElement = e.target.matches('[data-theme]') ? e.target : e.target.closest('[data-theme]');
                const themeName = themeElement.getAttribute('data-theme');
                this.switchTheme(themeName);
                e.preventDefault();
            }
        });
    }
    
    updateThemeSelector() {
        // Update any theme selector UI elements
        const themeItems = document.querySelectorAll('[data-theme]');
        themeItems.forEach(item => {
            const themeName = item.getAttribute('data-theme');
            const isActive = themeName === this.currentTheme;
            
            // Update active state
            item.classList.toggle('active', isActive);
            
            // Update check mark or active indicator
            const checkIcon = item.querySelector('.theme-check');
            if (checkIcon) {
                checkIcon.style.display = isActive ? 'inline' : 'none';
            }
        });
        
        // Update current theme indicator
        const currentThemeIndicator = document.querySelector('#currentThemeIndicator');
        if (currentThemeIndicator) {
            const theme = this.themes[this.currentTheme];
            currentThemeIndicator.innerHTML = `<i class="${theme.icon} me-2"></i>${theme.name}`;
        }
    }
    
    getCurrentTheme() {
        return this.currentTheme;
    }
}

// Initialize theme manager
const themeManager = new ThemeManager();

// Export for global access
window.themeManager = themeManager;
