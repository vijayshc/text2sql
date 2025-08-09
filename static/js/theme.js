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
                    '--light-bg': '#161616',
                    '--dark-bg': '#1a1a1a',
                    '--card-bg': '#1f1f1f',
                    '--sidebar-bg': '#1a1a1a',
                    '--text-primary': '#ffffff',
                    '--text-secondary': '#b0b0b0',
                    '--text-muted': '#808080',
                    '--border-color': '#2d2d2d',
                    '--hover-bg': '#2a2a2a'
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
                    '--light-bg': '#ffffff',
                    '--dark-bg': '#f8fafc',
                    '--card-bg': '#ffffff',
                    '--sidebar-bg': '#f8fafc',
                    '--text-primary': '#1f2937',
                    '--text-secondary': '#374151',
                    '--text-muted': '#6b7280',
                    '--border-color': '#e5e7eb',
                    '--hover-bg': '#f3f4f6'
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
                    '--light-bg': '#ffffff',
                    '--dark-bg': '#f8fafc',
                    '--card-bg': '#ffffff',
                    '--sidebar-bg': '#f0f7ff',
                    '--text-primary': '#1f2937',
                    '--text-secondary': '#374151',
                    '--text-muted': '#6b7280',
                    '--border-color': '#e5e7eb',
                    '--hover-bg': '#f3f4f6'
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
