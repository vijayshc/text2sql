# Flask to Flask API + Vue.js + Tailwind CSS Migration Plan

## Overview
Migrate the Text2SQL application from Flask with HTML/JavaScript frontend to:
- **Backend**: Flask API-only service
- **Frontend**: Vue.js 3 with Composition API
- **Styling**: Tailwind CSS

## Current Architecture Analysis

### Backend (Flask)
- **Main App**: 790-line app.py with extensive route handling
- **Routes**: 19 separate route files covering:
  - Authentication & Authorization (RBAC)
  - Admin Dashboard & User Management
  - Text2SQL Query Processing
  - Knowledge Base Q&A
  - Database Schema Management
  - Agent Mode (MCP integration)
  - Data Mapping Analysis
  - Vector Database Management
  - Configuration Management

### Frontend (HTML/JavaScript)
- **Templates**: 29 Jinja2 HTML templates
- **JavaScript**: 29 JS files for various functionalities
- **Styling**: Bootstrap 5 + custom CSS themes
- **Key Features**:
  - Complex dashboard with tabs and modals
  - Real-time query processing with progress tracking
  - Interactive schema viewer
  - Chat-like interfaces for knowledge base and agent mode
  - Data visualization with Chart.js
  - Monaco editor integration for SQL editing

## Migration Tasks

### Phase 1: Backend API Migration ✅ READY TO START

#### 1.1 API Infrastructure Setup
- [ ] **Task 1.1.1**: Create separate API configuration
  - Create `config/api_config.py` for API-specific settings
  - Configure CORS for frontend separation
  - Set up API versioning structure (`/api/v1/...`)
  - **Files to modify**: `config/config.py`, create new API config
  - **Estimated time**: 2 hours

- [ ] **Task 1.1.2**: Implement JWT Authentication
  - Replace session-based auth with JWT tokens
  - Create token generation and validation middleware
  - Update user authentication routes
  - **Files to modify**: `src/routes/auth_routes.py`, `src/utils/auth_utils.py`
  - **Estimated time**: 4 hours

#### 1.2 Route Conversion to API Endpoints
- [ ] **Task 1.2.1**: Convert core query routes
  - `/api/query` → Enhanced with proper API responses
  - `/api/schema` → Standardized API format
  - `/api/feedback` → RESTful API design
  - **Files to modify**: `app.py`, create `src/routes/api/query_api.py`
  - **Estimated time**: 3 hours

- [ ] **Task 1.2.2**: Convert authentication routes
  - Login/logout API endpoints
  - Password change/reset APIs
  - User profile management APIs
  - **Files to modify**: `src/routes/auth_routes.py`
  - **Estimated time**: 2 hours

- [ ] **Task 1.2.3**: Convert admin routes
  - User management APIs
  - Role/permission management APIs
  - Configuration management APIs
  - **Files to modify**: `src/routes/admin_*.py`
  - **Estimated time**: 4 hours

- [ ] **Task 1.2.4**: Convert knowledge base routes
  - Document upload/management APIs
  - Knowledge search APIs
  - Vector database management APIs
  - **Files to modify**: `src/routes/knowledge_routes.py`, `src/routes/vector_db_routes.py`
  - **Estimated time**: 3 hours

- [ ] **Task 1.2.5**: Convert specialized routes
  - Agent mode APIs
  - Data mapping APIs
  - Schema management APIs
  - MCP server management APIs
  - **Files to modify**: `src/routes/agent_routes.py`, `src/routes/data_mapping_routes.py`, etc.
  - **Estimated time**: 5 hours

#### 1.3 API Testing and Documentation
- [ ] **Task 1.3.1**: Create API test suite
  - Unit tests for all API endpoints
  - Integration tests for authentication flow
  - **Files to create**: `tests/api/` directory
  - **Estimated time**: 3 hours

- [ ] **Task 1.3.2**: API documentation
  - OpenAPI/Swagger documentation
  - Postman collection for testing
  - **Files to create**: `docs/api.md`, swagger specs
  - **Estimated time**: 2 hours

### Phase 2: Vue.js Frontend Setup

#### 2.1 Project Initialization
- [ ] **Task 2.1.1**: Initialize Vue.js project
  - Create Vue 3 project with Vite
  - Configure TypeScript support
  - Set up project structure
  - **Directory to create**: `frontend/`
  - **Estimated time**: 2 hours

- [ ] **Task 2.1.2**: Configure Tailwind CSS
  - Install and configure Tailwind CSS
  - Set up custom design tokens
  - Create utility classes for app-specific styling
  - **Files to create**: `frontend/tailwind.config.js`, base styles
  - **Estimated time**: 2 hours

- [ ] **Task 2.1.3**: Set up development environment
  - Configure Vue Router for SPA navigation
  - Install and configure Pinia for state management
  - Set up axios for API communication
  - Configure development proxy for API calls
  - **Files to create**: Router, store, and API service files
  - **Estimated time**: 3 hours

#### 2.2 Core Infrastructure
- [ ] **Task 2.2.1**: Create API service layer
  - HTTP client configuration with interceptors
  - Authentication token management
  - Error handling and retry logic
  - **Files to create**: `frontend/src/services/api.js`
  - **Estimated time**: 3 hours

- [ ] **Task 2.2.2**: Implement state management
  - User authentication store
  - Application configuration store
  - UI state management (modals, loading states)
  - **Files to create**: `frontend/src/stores/` directory
  - **Estimated time**: 3 hours

- [ ] **Task 2.2.3**: Create utility components
  - Loading spinners and progress indicators
  - Error boundary components
  - Form validation components
  - **Files to create**: `frontend/src/components/common/`
  - **Estimated time**: 3 hours

### Phase 3: Core Component Migration

#### 3.1 Layout and Navigation
- [ ] **Task 3.1.1**: Create main layout components
  - App shell component
  - Sidebar navigation component
  - Header component with user menu
  - **Files to create**: `frontend/src/components/layout/`
  - **Reference**: `templates/base.html`, `templates/index.html`
  - **Estimated time**: 4 hours

- [ ] **Task 3.1.2**: Implement responsive design
  - Mobile-first responsive layout
  - Sidebar collapse/expand functionality
  - Theme switching capability
  - **Files to modify**: Layout components, Tailwind config
  - **Estimated time**: 3 hours

#### 3.2 Authentication System
- [ ] **Task 3.2.1**: Create authentication pages
  - Login page component
  - Password change component
  - User profile component
  - **Files to create**: `frontend/src/views/auth/`
  - **Reference**: `templates/auth/`
  - **Estimated time**: 4 hours

- [ ] **Task 3.2.2**: Implement auth guards and routing
  - Route protection based on authentication
  - Role-based access control
  - Automatic token refresh
  - **Files to modify**: Router configuration, auth store
  - **Estimated time**: 2 hours

#### 3.3 Main Dashboard
- [ ] **Task 3.3.1**: Create home/dashboard page
  - Query input component with table mentions
  - Progress tracking component
  - Results display with tabs (Results, SQL, Steps, Dashboard)
  - **Files to create**: `frontend/src/views/Home.vue`, related components
  - **Reference**: `templates/index.html`, `static/js/query-handler.js`
  - **Estimated time**: 6 hours

- [ ] **Task 3.3.2**: Implement query functionality
  - Query submission and progress tracking
  - Real-time result updates
  - SQL editor integration (Monaco)
  - Chart visualization (Chart.js)
  - **Files to create**: Query-related components and composables
  - **Reference**: Multiple JS files for query handling
  - **Estimated time**: 8 hours

### Phase 4: Feature Migration

#### 4.1 Schema Management
- [ ] **Task 4.1.1**: Schema viewer component
  - Interactive schema display
  - Table and column filtering
  - Schema modal/popup functionality
  - **Files to create**: `frontend/src/components/schema/`
  - **Reference**: `templates/admin/schema.html`, schema JS files
  - **Estimated time**: 4 hours

#### 4.2 Knowledge Base
- [ ] **Task 4.2.1**: Knowledge base interface
  - Document upload component
  - Knowledge search interface
  - Chat-like Q&A interface
  - **Files to create**: `frontend/src/views/Knowledge.vue`, related components
  - **Reference**: `templates/knowledgebase.html`, knowledge JS files
  - **Estimated time**: 5 hours

#### 4.3 Admin Dashboard
- [ ] **Task 4.3.1**: Admin overview page
  - Statistics dashboard
  - Quick action cards
  - Recent activity display
  - **Files to create**: `frontend/src/views/admin/Dashboard.vue`
  - **Reference**: `templates/admin/index.html`
  - **Estimated time**: 4 hours

- [ ] **Task 4.3.2**: User management interface
  - User list with DataTable equivalent
  - User creation/editing forms
  - Role assignment interface
  - **Files to create**: `frontend/src/views/admin/Users.vue`
  - **Reference**: `templates/admin/users.html`
  - **Estimated time**: 5 hours

- [ ] **Task 4.3.3**: Configuration management
  - Settings form components
  - Dynamic configuration display
  - Validation and error handling
  - **Files to create**: `frontend/src/views/admin/Config.vue`
  - **Reference**: `templates/admin/config.html`
  - **Estimated time**: 3 hours

#### 4.4 Specialized Features
- [ ] **Task 4.4.1**: Agent mode interface
  - Chat interface for agent interactions
  - MCP server management
  - Tool confirmation dialogs
  - **Files to create**: `frontend/src/views/Agent.vue`, related components
  - **Reference**: `templates/agent_mode.html`, agent JS files
  - **Estimated time**: 6 hours

- [ ] **Task 4.4.2**: Data mapping interface
  - Data mapping analysis tools
  - Interactive mapping visualization
  - Bulk analysis functionality
  - **Files to create**: `frontend/src/views/DataMapping.vue`
  - **Reference**: `templates/data_mapping/`, mapping JS files
  - **Estimated time**: 5 hours

- [ ] **Task 4.4.3**: Query editor
  - Advanced SQL editor with Monaco
  - Query execution and result display
  - Query history and saving
  - **Files to create**: `frontend/src/views/QueryEditor.vue`
  - **Reference**: `templates/query_editor.html`, editor JS files
  - **Estimated time**: 4 hours

### Phase 5: Testing and Finalization

#### 5.1 Quality Assurance
- [ ] **Task 5.1.1**: Component testing
  - Unit tests for all Vue components
  - Integration tests for user flows
  - API integration testing
  - **Files to create**: `frontend/tests/` directory
  - **Estimated time**: 6 hours

- [ ] **Task 5.1.2**: End-to-end testing
  - Critical user journey testing
  - Cross-browser compatibility
  - Mobile responsiveness testing
  - **Tools**: Cypress or Playwright
  - **Estimated time**: 4 hours

#### 5.2 Performance and Optimization
- [ ] **Task 5.2.1**: Performance optimization
  - Code splitting and lazy loading
  - Bundle size optimization
  - API response caching
  - **Estimated time**: 3 hours

- [ ] **Task 5.2.2**: Production build setup
  - Build optimization for production
  - Environment configuration
  - Docker configuration updates
  - **Estimated time**: 2 hours

#### 5.3 Documentation and Deployment
- [ ] **Task 5.3.1**: Update documentation
  - Update README with new setup instructions
  - Create deployment guide
  - Update user documentation
  - **Estimated time**: 3 hours

- [ ] **Task 5.3.2**: Deployment preparation
  - Production deployment scripts
  - Environment variable configuration
  - Nginx configuration for SPA
  - **Estimated time**: 2 hours

## File Structure Planning

### New Backend Structure
```
app.py (API-only)
├── src/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── query.py
│   │   │   ├── admin.py
│   │   │   ├── knowledge.py
│   │   │   └── ...
│   ├── middleware/
│   │   ├── auth.py
│   │   ├── cors.py
│   │   └── error_handler.py
│   └── (existing structure)
```

### New Frontend Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── common/
│   │   ├── layout/
│   │   ├── forms/
│   │   └── ...
│   ├── views/
│   │   ├── Home.vue
│   │   ├── auth/
│   │   ├── admin/
│   │   └── ...
│   ├── stores/
│   ├── services/
│   ├── composables/
│   ├── router/
│   └── assets/
├── public/
├── tests/
└── package.json
```

## Risk Mitigation

1. **Functionality Loss Risk**: Maintain detailed feature checklist and test each migrated component
2. **Data Loss Risk**: Backup database before any structural changes
3. **Authentication Issues**: Thoroughly test JWT implementation before removing session auth
4. **Performance Degradation**: Monitor API response times and frontend bundle size
5. **User Experience**: Maintain UI/UX consistency during migration

## Success Criteria

- [ ] All existing functionality preserved and working
- [ ] API provides same capabilities as current backend
- [ ] Vue.js frontend matches current UI/UX
- [ ] Tailwind CSS provides consistent styling
- [ ] Performance equal or better than current implementation
- [ ] All tests passing
- [ ] Documentation updated and comprehensive

## Total Estimated Time: ~120 hours

**Phase 1**: 28 hours  
**Phase 2**: 10 hours  
**Phase 3**: 25 hours  
**Phase 4**: 42 hours  
**Phase 5**: 15 hours  

## Next Steps

1. Start with Phase 1, Task 1.1.1: API Infrastructure Setup
2. Complete each phase sequentially with verification
3. Mark tasks as completed in this document
4. Regular commits and progress reporting throughout migration