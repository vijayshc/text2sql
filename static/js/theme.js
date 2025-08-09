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
                    '--syntax-comment': '#5c6370',
                    '--primary-gradient': 'linear-gradient(135deg, #ffffff, #e5e5e5)',
                    '--card-gradient': 'linear-gradient(145deg, #1f1f1f, #252525)',
                    '--sidebar-gradient': '#1a1a1a',
                    '--transition-speed': '0.2s'
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
                    // Light theme uses neutral buttons
                    '--button-primary-bg': '#111827',
                    '--button-primary-text': '#ffffff',
                    '--button-primary-hover': '#1f2937',
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
                    '--syntax-comment': '#6b7280',
                    '--primary-gradient': 'linear-gradient(135deg, #111827, #1f2937)',
                    '--card-gradient': 'linear-gradient(145deg, #ffffff, #f8fafc)',
                    '--sidebar-gradient': '#f8fafc',
                    '--sidebar-active-bg': 'rgba(17, 24, 39, 0.08)',
                    '--sidebar-active-border': '#111827',
                    '--transition-speed': '0.2s'
                }
            },
            lightColored: {
                name: 'Light Colored',
                icon: 'fas fa-palette',
                colors: {
                    // Deeper blue palette aligned with themes.css
                    '--primary-color': '#1f5bd8',
                    '--secondary-color': '#123a99',
                    '--accent-color': '#3c7af2',
                    '--success-color': '#10b981',
                    '--warning-color': '#f59e0b',
                    '--danger-color': '#ef4444',
                    '--info-color': '#3b82f6',
                    '--light-bg': '#ffffff',
                    '--dark-bg': '#f8fafc',
                    '--card-bg': '#ffffff',
                    '--sidebar-bg': '#1f5bd8',
                    '--text-primary': '#1f2937',
                    '--text-secondary': '#374151',
                    '--text-muted': '#6b7280',
                    '--border-color': '#e5e7eb',
                    '--hover-bg': '#f3f4f6',
                    '--input-bg': '#ffffff',
                    '--input-border': '#d1d5db',
                    '--input-focus-border': '#3b82f6',
                    '--table-header-bg': '#1f5bd8',
                    '--table-header-text': '#ffffff',
                    '--table-row-bg': '#ffffff',
                    '--table-row-hover': '#f0f7ff',
                    '--table-border': '#e5e7eb',
                    '--button-primary-bg': '#1f5bd8',
                    '--button-primary-text': '#ffffff',
                    '--button-primary-hover': '#1549b9',
                    '--button-secondary-bg': '#e8f1ff',
                    '--button-secondary-text': '#123a99',
                    '--button-secondary-hover': '#d1e3ff',
                    '--card-shadow': '0 2px 8px rgba(31, 91, 216, 0.12)',
                    '--card-shadow-hover': '0 4px 12px rgba(31, 91, 216, 0.18)',
                    '--overlay-bg': 'rgba(0, 0, 0, 0.3)',
                    '--focus-ring': 'rgba(59, 130, 246, 0.3)',
                    '--scrollbar-track': '#e8f1ff',
                    '--scrollbar-thumb': '#b1ccff',
                    '--syntax-keyword': '#7c3aed',
                    '--syntax-string': '#059669',
                    '--syntax-number': '#dc2626',
                    '--syntax-function': '#2563eb',
                    '--syntax-comment': '#6b7280',
                    '--primary-gradient': 'linear-gradient(135deg, #1f5bd8, #123a99)',
                    '--card-gradient': 'linear-gradient(145deg, #ffffff, #eaf3ff)',
                    '--sidebar-gradient': '#1f5bd8',
                    '--sidebar-active-bg': 'rgba(255, 255, 255, 0.18)',
                    '--sidebar-active-border': '#ffffff',
                    '--transition-speed': '0.2s'
                }
            }
        };
        
    // Default to light theme when no preference is stored
    this.currentTheme = this.getStoredTheme() || 'light';
        this.init();
    }
    
    init() {
        // Apply stored theme on page load
        this.applyTheme(this.currentTheme);
        
        // Listen for theme change events immediately
        this.attachEventListeners();
        
        // Also attach after DOM is ready for any dynamically loaded content
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.updateThemeSelector();
            });
        } else {
            this.updateThemeSelector();
        }
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
            console.warn(`Theme '${themeName}' not found, falling back to light theme`);
            themeName = 'light';
            return this.applyTheme(themeName);
        }

        const root = document.documentElement;
        
        // Apply CSS custom properties
        Object.entries(theme.colors).forEach(([property, value]) => {
            root.style.setProperty(property, value);
        });
        
        // Update theme class on both html and body without nuking other classes
        const updateThemeClass = (el) => {
            if (!el) return;
            const classes = Array.from(el.classList);
            classes.filter(c => c.startsWith('theme-')).forEach(c => el.classList.remove(c));
            el.classList.add(`theme-${themeName}`);
        };
        updateThemeClass(document.body);
        updateThemeClass(document.documentElement);
        
        // Update highlight.js theme based on current theme
        this.updateHighlightTheme(themeName);
        
        // Store the current theme
        this.currentTheme = themeName;
        this.storeTheme(themeName);
        
        // Update the theme selector UI
        this.updateThemeSelector();        // Dispatch custom event for components that need to react to theme changes
        document.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme: themeName, colors: theme.colors }
        }));
        
        console.log(`Applied theme: ${theme.name}`);
    }
    
    updateHighlightTheme(themeName) {
        const highlightLink = document.getElementById('highlight-theme');
        if (highlightLink) {
            // Map our themes to appropriate highlight.js themes
            const highlightThemes = {
                dark: 'github-dark',
                light: 'github',
                lightColored: 'github'
            };
            
            const highlightTheme = highlightThemes[themeName] || 'github-dark';
            const newHref = `https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/${highlightTheme}.min.css`;
            
            // Only update if the theme is different
            if (highlightLink.href !== newHref) {
                highlightLink.href = newHref;
                console.log(`Applied highlight.js theme: ${highlightTheme}`);
            }
        }
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
            const themeElement = e.target.closest('[data-theme]');
            if (themeElement) {
                const themeName = themeElement.getAttribute('data-theme');
                if (this.themes[themeName]) {
                    this.switchTheme(themeName);
                    e.preventDefault();
                }
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
