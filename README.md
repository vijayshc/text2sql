# Text2SQL Assistant

A comprehensive AI-powered database query assistant built with modern Vue.js 3 Single Page Application (SPA) architecture and Flask API backend, featuring advanced enterprise capabilities including admin management, AI agents, and vector search.

## 🏗️ Modern Architecture

This application has been completely migrated to a **modern Vue.js 3 + Flask API architecture** with **zero backward compatibility** with the previous server-side rendering approach.

### Architecture Overview

**Frontend (Vue.js 3 SPA)**
- 🎨 **Vue.js 3** with **TypeScript** for type safety and modern development
- 🎯 **23 Responsive Views** covering all functionality (10 user + 13 admin views)
- 🎪 **Pinia** for centralized state management (auth, queries, UI state)
- 🎨 **Tailwind CSS** for modern, responsive design system
- 📱 **Client-side routing** with Vue Router for seamless navigation
- ⚡ **Vite** for lightning-fast development and optimized builds
- 🧪 **Comprehensive testing** with Vitest (unit) and Playwright (e2e)

**Backend (Flask API-Only)**
- 🚀 **Pure RESTful API** under `/api/v1/` and `/api/v1/admin/`
- 🔐 **JWT Authentication** with automatic token refresh and secure management
- 📡 **Server-Sent Events (SSE)** for real-time streaming features
- 🛡️ **CORS Configuration** for secure cross-origin requests
- 📊 **Comprehensive error handling** with structured JSON responses
- 🔄 **No HTML template rendering** - API-first architecture

### Complete Feature Parity

**All Original Functionality Preserved:**
- ✅ Natural language to SQL conversion
- ✅ Database interaction and query execution
- ✅ Schema awareness and management
- ✅ Knowledge base Q&A with document upload
- ✅ Database metadata search with AI
- ✅ User management and RBAC
- ✅ **All 13 admin features** fully migrated
- ✅ Agent mode with MCP server integration
- ✅ Data mapping analysis
- ✅ Vector database management
- ✅ Audit logging and monitoring

## 🎯 Vue.js Frontend Features

The Vue.js 3 frontend provides a modern, responsive Single Page Application with **23 comprehensive views**:

### User Views (10 Views)
- 🏠 **HomeView** - Main dashboard with workspace management and query interface
- 🔐 **LoginView** - Secure JWT-based authentication
- 👤 **ProfileView** - User profile management and permissions display
- 🔑 **ChangePasswordView** - Secure password change with real-time validation
- 🔄 **ResetPasswordRequestView** - Email-based password reset initiation
- 🔄 **ResetPasswordView** - Secure password reset completion
- ✏️ **QueryEditorView** - Advanced SQL editor with syntax highlighting and AI assistance
- 📚 **KnowledgeView** - Document upload, Q&A chat interface with AI
- 🗄️ **SchemaView** - Database schema browser with workspace and table management
- 🔍 **MetadataSearchView** - AI-powered semantic search with conversation history
- 🤖 **AgentView** - Interactive AI agent with MCP server integration
- 📊 **DataMappingView** - AI-powered data mapping analysis with streaming capabilities

### Admin Views (13 Views) - Complete Migration
- 📊 **AdminDashboardView** - System statistics, quick actions, and performance metrics
- 📝 **AdminSamplesView** - SQL sample management with full CRUD operations
- 👥 **AdminUsersView** - User management with role assignment and status control
- 🛡️ **AdminRolesView** - Role creation, editing, and permission management
- 🔧 **AdminMCPServersView** - MCP server management with start/stop and configuration
- 🧠 **AdminSkillLibraryView** - AI skills/prompts management with vectorization and import/export
- 📚 **AdminKnowledgeView** - Admin document upload and text content management
- 🗄️ **AdminVectorDBView** - Vector database administration with collection and record management
- 💾 **AdminDatabaseQueryView** - Direct SQL query interface with schema browser and execution
- ⚙️ **AdminConfigView** - System configuration management with type validation and categories
- 📋 **AdminAuditView** - Complete activity monitoring with CSV export and filtering

### Modern Frontend Features
- 🎨 **Responsive Design** - Mobile-first approach with Tailwind CSS
- 🌙 **Dark/Light Theme** - User preference with persistent storage
- 🔔 **Toast Notifications** - Real-time feedback with styled alerts
- 📡 **Real-time Streaming** - Server-Sent Events for AI responses
- 🔐 **JWT Token Management** - Automatic refresh and secure storage
- 🧪 **Type Safety** - Full TypeScript integration with proper type definitions
- ⚡ **Performance Optimized** - Code splitting, lazy loading, and optimized builds

## 🚀 API Architecture

The backend provides a comprehensive RESTful API that serves the Vue.js frontend with structured endpoints:

### Core API Endpoints (`/api/v1/`)
- **Authentication:** `/api/v1/auth/` - Login, logout, token refresh, password management
- **Query Processing:** `/api/v1/query/` - Natural language to SQL conversion and execution
- **Agent Mode:** `/api/v1/agent/` - AI agent interactions with MCP server integration
- **Data Mapping:** `/api/v1/data-mapping/` - AI-powered data mapping analysis with streaming
- **Schema Management:** `/api/v1/schema/` - Database schema operations and workspace management
- **Metadata Search:** `/api/v1/metadata-search/` - AI semantic search with conversation history
- **Knowledge Base:** `/api/v1/feedback/` - Document management and Q&A system
- **Health Monitoring:** `/api/health` - Application health check and status

### Admin API Endpoints (`/api/v1/admin/`)
- **Dashboard:** Statistics, system metrics, and quick actions
- **User Management:** User CRUD operations, role assignments, status management
- **Role Management:** Role creation, permission assignment, RBAC administration
- **Sample Management:** SQL sample CRUD with categorization and search
- **Skill Library:** AI skills management with vectorization and import/export
- **Knowledge Management:** Admin document upload and content management
- **Vector Database:** Collection management, record operations, search administration
- **Database Queries:** Direct SQL execution interface with schema browser
- **Configuration:** System settings management with type validation
- **MCP Servers:** Server management with start/stop, configuration, and monitoring
- **Audit Logs:** Activity monitoring with filtering and CSV export

### API Features
- **JWT Authentication** - Stateless authentication with automatic token refresh
- **CORS Support** - Configured for secure cross-origin requests
- **Streaming Responses** - Server-Sent Events for real-time AI interactions
- **Error Handling** - Comprehensive error responses with structured JSON
- **Request Validation** - Input validation and sanitization across all endpoints
- **Rate Limiting** - Protection against abuse on sensitive endpoints

## Comprehensive Audit Logging

The application now features comprehensive audit logging across all backend operations to support performance reviews and compliance requirements:

### Audit Events Captured:
* **Knowledge Base Operations:**
  - Document uploads and processing
  - Text content additions
  - Document deletions and tag management
  - Knowledge queries (both regular and streaming) with full input/output capture
  - Knowledge base search operations

* **Metadata Search Operations:**
  - Schema metadata processing and statistics
  - Metadata search queries (streaming and non-streaming) with complete response capture
  - Admin metadata management activities

* **Query Editor Events:**
  - Query editor page access
  - SQL query executions with full query text and results
  - AI-powered query completions
  - Query saves and management operations

* **Agent Mode Operations:**
  - Agent chat interactions with streaming response capture
  - MCP server selections and connections
  - Tool execution confirmations and results
  - Server status checks and configurations

* **Database Administration:**
  - Database query editor access
  - Direct SQL query executions in admin interface
  - Database schema retrieval operations

* **Schema Management:**
  - Workspace creation, updates, and deletions
  - Table creation, modifications, and removals
  - Schema import/export operations
  - Join condition management

* **Data Mapping Operations:**
  - Data mapping page access and server status checks
  - Column analysis and bulk analysis operations
  - Mapping saves and repository searches

* **System Operations:**
  - User authentication and authorization events
  - Table suggestions and workspace retrievals
  - Sample management (create, update, delete)
  - Feedback submissions and statistics

### Audit Log Features:
* **Complete Input/Output Capture:** All queries and responses are logged, including streaming responses
* **User Context:** User ID, IP address, and timestamp for all operations
* **Performance Metrics:** Response lengths and processing details for performance analysis
* **Error Tracking:** Failed operations with detailed error messages
* **Streaming Support:** Special handling for streaming operations to capture complete responses
* **Response Limiting:** Audit responses are limited to 1000 characters to prevent log bloat while maintaining useful information

### Security and Compliance:
* **Data Privacy:** Sensitive information is handled appropriately in audit logs
* **Retention Policies:** Audit logs support filtering and export for compliance requirements
* **Access Control:** Audit log viewing requires appropriate permissions
* **Export Capabilities:** Audit logs can be exported as CSV for external analysis

## Sensitive Tool Confirmation:** Requires user approval before executing potentially sensitive operations like shell commands.
  
  This feature adds an intermediate confirmation dialog whenever the agent attempts to run sensitive tools (e.g., `run_bash_shell`). Users will receive a popup showing the tool name and arguments, and must confirm or cancel execution. If canceled, the operation is aborted and the agent stops processing further.

## MCP Skill Library Server

The application includes a built-in MCP Skill Library Server that acts as an enterprise skill repository for agent mode:

* **Skill Management:** Create, edit, and manage enterprise-specific task execution patterns and procedures
* **Vector Search:** AI-powered semantic search to find relevant skills based on natural language queries
* **Category Organization:** Skills organized by categories (data engineering, automation, security, etc.)
* **HTTP/SSE Interface:** Runs as an independent MCP server accessible via HTTP with Server-Sent Events
* **Agent Integration:** LLMs can search the skill library to learn how to perform complex enterprise tasks
* **Step-by-Step Guidance:** Each skill provides detailed technical steps, prerequisites, and examples

### Skill Library Features:
- **Pure Vector Search:** Find skills using natural language queries with semantic similarity search (no hardcoded filtering)
- **Dynamic Categories:** Skills organized by categories dynamically retrieved from the database
- **Detailed Documentation:** Each skill includes prerequisites, step-by-step instructions, and usage examples
- **Version Control:** Skills are versioned and can be updated or deprecated
- **Admin Interface:** Web-based management interface for creating and editing skills
- **MCP Protocol Compliance:** Proper MCP server implementation using FastMCP with SSE transport
- **Vector Embedding:** Skills are embedded for semantic similarity search

### Available Skill Categories:
Categories are dynamically managed through the admin interface and retrieved from the database. Common categories include:
- **Data Engineering:** Data pipeline creation, ETL processes, data transformation
- **Database Management:** Database operations, schema management, optimization  
- **Machine Learning:** ML model development, training, deployment
- **DevOps:** Deployment, infrastructure management, CI/CD
- **Security:** Security implementation, compliance, access control
- **Automation:** Process automation, scripting, workflow automation
- **Testing:** Testing frameworks, quality assurance, validation
- **Integration:** System integration, API development, data connections
- **Reporting:** Report generation, dashboard creation, visualization
- **Monitoring:** System monitoring, alerting, performance tracking

**Note:** Categories are no longer hardcoded and can be customized through the admin interface.

## MCP Server Management

The application now supports managing multiple Model Context Protocol (MCP) servers:

* **Server Types:** Support for both stdio (command-line process) and HTTP/SSE servers
* **Admin Interface:** Add, configure, start/stop, and monitor MCP servers
* **Auto-Selection:** The system can intelligently select the most appropriate MCP server for each user query
* **Server State Persistence:** MCP server state (running/stopped) is preserved across application restarts
* **Tool Discovery:** View available tools for each MCP server through the admin interface
* **Unified LLM Integration:** All MCP servers now use the common LLM engine for consistent behavior and configuration

## AI Data Mapping Analyst

The AI Data Mapping Analyst is an advanced enterprise-grade system that replicates expert data architect workflows for data warehousing and data mart development:

### Core Capabilities:
* **Intelligent Column Mapping:** AI-powered analysis to map source columns to target warehouse/mart structures
* **Granularity Analysis:** Automated assessment of data granularity compatibility between source and target
* **Join Path Discovery:** Graph-based algorithms to find optimal join paths between tables using NetworkX
* **Semantic Column Matching:** Advanced semantic analysis to identify similar columns across different naming conventions
* **Transformation Logic Generation:** Auto-generation of ETL transformation logic including aggregations and calculations
* **New Table Proposals:** AI recommendations for new dimension/fact table structures when mapping is not feasible

### Architecture:
* **MCP Server Integration:** Dedicated MCP server (`mcp_data_mapping_server.py`) with 8 specialized tools
* **Cognitive Agent Workflow:** Master workflow orchestrating tool calls to replicate expert decision-making
* **Metadata Management:** JSON-based data catalog with comprehensive table/column definitions and business context
* **Web Interface:** Comprehensive UI with single/bulk analysis, mapping repository, and detailed result views
* **Vector Storage Support:** Integration with ChromaDB for semantic search and similarity matching

### Available Tools:
1. **get_column_mapping:** Retrieve existing mappings from the repository
2. **analyze_unmapped_column:** Deep analysis of unmapped columns with business context
3. **find_candidate_tables:** Identify potential target tables using semantic and structural analysis
4. **analyze_granularity_fit:** Assess data granularity compatibility between source and targets
5. **find_join_path:** Calculate optimal join paths using graph algorithms
6. **find_semantic_column_matches:** Identify semantically similar columns across schemas
7. **generate_etl_logic:** Generate complete ETL transformation expressions with business rules
8. **propose_new_table_structure:** AI-powered proposals for new warehouse structures

### Usage Scenarios:
* **Enterprise Data Warehouse Design:** Map operational data to dimensional model structures
* **Data Mart Development:** Create subject-specific data marts with appropriate granularity
* **Legacy System Migration:** Map legacy schemas to modern data warehouse architectures
* **Data Lineage Documentation:** Maintain comprehensive data lineage and transformation documentation
* **ETL Development:** Generate ETL logic for complex transformations and aggregations

### Technical Features:
* **Async Operations:** Full async/await support for handling complex analysis workflows
* **Progress Tracking:** Real-time progress updates for long-running analysis operations
* **Bulk Analysis:** Process multiple columns simultaneously with detailed status reporting
* **Mapping Repository:** Version-controlled repository for approved mappings with search and filtering
* **Export Capabilities:** Generate DDL scripts and ETL code from analysis results

## Code Architecture Improvements

Recent updates have improved the codebase architecture:

* **Common LLM Engine:** Centralized LLM management through `src/utils/common_llm.py` providing a shared instance across all components
* **Unified Tool Calling:** All MCP client interactions now use the same LLM engine for tool calling operations
* **Consistent Configuration:** Single source of truth for LLM configuration (model, temperature, max_tokens) across the application
* **Better Error Handling:** Improved error handling and retry logic for MCP server communications
* **Multi-Format Support:** Support for both OpenAI and Llama message formats with configurable switching

## Message Format Support

The application now supports multiple message formats for different LLM providers:

* **OpenAI Format:** Standard OpenAI message format with native tool calling support
* **Llama Format:** Custom Llama chat template format with tool calling implementation
* **Dynamic Switching:** Configure message format via environment variable `MESSAGE_FORMAT` (openai/llama)
* **Admin Interface:** Web-based interface to test and switch between message formats
* **Tool Calling:** Both formats support function/tool calling with automatic conversion
* **Testing Tools:** Built-in message format testing and preview functionality

### Llama Format Features:
- Custom chat template using `<|begin_of_text|>`, `<|start_header_id|>`, and `<|eot_id|>` tokens
- Tool definitions embedded directly in the prompt
- Function call responses in JSON format: `{"tool_calls": [{"name": "func_name", "arguments": {...}}]}`
- Robust JSON parsing with fallback to natural language extraction
- Automatic conversion between OpenAI and Llama formats
- Support for conversation history and multi-turn interactions
- Improved event loop management for HTTP/SSE MCP connections
- Enhanced error handling and connection recovery

### Configuration:
Set `MESSAGE_FORMAT=llama` in your `.env` file to use Llama format, or `MESSAGE_FORMAT=openai` (default) for OpenAI format.

## Key Features

*   **Natural Language to SQL:** Converts English questions to SQL.
*   **Database Interaction:** Executes SQL and shows results.
*   **Schema Awareness:** Uses database schema details for better query generation.
*   **Knowledge Base Q&A:** Answers questions based on uploaded documents or directly pasted text using vector search with conversational support.
*   **Database Metadata Search:** Search and explore database schema with conversational context and enhanced accuracy using query reformatting and BM25 reranking.
*   **Conversational Support:** Both knowledge base and metadata search now support follow-up questions with configurable conversation history limits.
*   **User Feedback:** Collects feedback to refine query generation.
*   **Sample Management:** Uses curated and successful past queries as examples for the AI.
*   **User Management & RBAC:** Secure login, user roles, and permissions.
*   **Admin Dashboard:** Tools for user/role management, audit logs, and system monitoring.
*   **Admin DB Query Editor:** Interface for admins to execute raw SQL queries.
*   **Configuration Management UI:** Allows admins to manage application settings via the UI.
*   **Metadata Search:** Functionality to search database metadata.
*   **SQL Query Editor:** A dedicated interface for writing/editing SQL queries.
*   **Manual SQL Editor with Monaco Integration:** View, edit, and execute AI-generated SQL directly in a Monaco-powered editor within the SQL tab.
*   **Vector DB Management UI:** Interface for admins to manage the vector database.
*   **MCP Server Management:** Admin interface to manage multiple MCP servers of both stdio and HTTP types.
*   **Multi-Server Agent:** Agent capable of working with multiple MCP servers and selecting the best server for each task.
*   **AI Data Mapping Analyst:** Advanced data mapping and lineage analysis using AI-powered MCP server and cognitive agent workflows.
*   **Security:** Includes features like CSRF protection, secure headers, and rate limiting.
*   **Sensitive Tool Confirmation:** Requires user approval before executing potentially sensitive operations like shell commands.
  
  This feature adds an intermediate confirmation dialog whenever the agent attempts to run sensitive tools (e.g., `run_bash_shell`). Users will receive a popup showing the tool name and arguments, and must confirm or cancel execution. If canceled, the operation is aborted and the agent stops processing further.

## Recent Updates

### MCP Connection Reliability Improvements (2025-06-27)

**Major Enhancement:** Implemented robust connection management for MCP servers to handle connection failures gracefully:

* **Per-Request Connection Pattern:** Fresh connections are established for each request instead of maintaining persistent connections, eliminating timeout and stale connection issues
* **Automatic Error Recovery:** Tool execution failures are automatically retried with progressive backoff (up to 3 attempts)
* **Graceful Error Handling:** Connection errors are handled in the backend without exposing technical details to users or the LLM
* **Resource Management:** Proper cleanup of connections after each request to prevent resource leaks
* **Enhanced Stability:** Eliminates "Runtime error during tool execution - server connection lost" errors
* **Improved User Experience:** Users see meaningful responses instead of technical error messages

**Technical Details:**
- Added `per_request_connection=True` mode as default for all new MCP clients
- Implemented `_execute_tool_with_recovery()` with intelligent retry logic
- Enhanced connection validation and event loop health checks
- Improved tool result formatting with fallback mechanisms

For detailed technical information, see [MCP_CONNECTION_IMPROVEMENTS.md](MCP_CONNECTION_IMPROVEMENTS.md).

## 🛠️ Tech Stack

**Frontend**
- **Vue.js 3** - Modern reactive framework with Composition API
- **TypeScript** - Type safety and enhanced developer experience
- **Tailwind CSS** - Utility-first CSS framework for responsive design
- **Pinia** - State management for auth, queries, and UI state
- **Vue Router** - Client-side routing for seamless navigation
- **Vite** - Fast build tool with hot module replacement
- **Axios** - HTTP client for API communication

**Backend**
- **Flask** - Lightweight Python web framework (API-only)
- **SQLAlchemy** - Database ORM and query builder
- **JWT** - JSON Web Tokens for stateless authentication
- **CORS** - Cross-Origin Resource Sharing support

**AI & Data**
- **Azure AI Inference Service** - Large language model integration
- **Sentence-Transformers** - Text embeddings for semantic search
- **OpenRouter** - Multi-provider AI service access
- **ChromaDB** - Vector database for similarity search
- **BM25** - Lexical search and reranking algorithms

**Infrastructure**
- **SQLite** - Default relational database (production-ready alternatives supported)
- **ChromaDB REST API Service** - Standalone vector database service
- **MCP Protocol** - Model Context Protocol for AI agent tool integration
- **Server-Sent Events (SSE)** - Real-time streaming for AI responses

## ⭐ Key Features

### Core Functionality
- 🔤 **Natural Language to SQL** - Converts English questions to optimized SQL queries
- 🗃️ **Database Interaction** - Execute SQL queries and display formatted results
- 🧠 **Schema Awareness** - Uses database schema details for accurate query generation
- 💡 **AI-Powered Assistance** - Intelligent query suggestions and completions
- 📊 **Sample Management** - Curated successful queries as examples for AI learning

### Advanced AI Features
- 📚 **Knowledge Base Q&A** - Upload documents and ask questions using vector search
- 🔍 **Metadata Search** - AI-powered database schema exploration with semantic search
- 🤖 **Agent Mode** - Interactive AI assistant with tool integration via MCP protocol
- 📊 **Data Mapping Analysis** - AI-powered data lineage and ETL logic generation
- 🧪 **Conversational Support** - Follow-up questions with configurable history limits

### Enterprise Features
- 👥 **User Management & RBAC** - Secure authentication with role-based permissions
- 📊 **Admin Dashboard** - Comprehensive management tools for all system components
- 📝 **Audit Logging** - Complete activity tracking for compliance and monitoring
- ⚙️ **Configuration Management** - System settings with validation and categorization
- 🗄️ **Vector Database Management** - Admin interface for vector operations and collections

### Development & Integration
- 🔧 **MCP Server Management** - Support for multiple Model Context Protocol servers
- 🔌 **Multi-Server Agent** - Intelligent server selection for optimal task execution
- 📡 **Real-time Streaming** - Server-Sent Events for live AI response updates
- 🛡️ **Security Features** - CSRF protection, secure headers, and rate limiting
- 📈 **Performance Monitoring** - Health checks and comprehensive logging

## ChromaDB Service Configuration

The ChromaDB service can be configured through `chromadb_service/config.py`:

```python
# Service Configuration
SERVICE_HOST = "localhost"      # Service host
SERVICE_PORT = 8001            # Service port  
DEBUG = False                  # Debug mode
CHROMADB_PERSIST_DIR = "../chroma_data"  # Data directory

# Embedding Configuration
EMBEDDING_MODEL = "all-MiniLM-L6-v2"    # Sentence transformer model
EMBEDDING_DIMENSION = 384               # Embedding dimension
```

## Enhanced Metadata Search

The metadata search functionality has been significantly improved for better accuracy:

### Key Improvements:

**1. Query Reformatting:** 
- User queries are automatically reformatted to match the schema vectorization format
- Converts natural language to structured format (e.g., "customer table" → "Table: customer")
- Improves vector search accuracy by aligning query format with stored schema data

**2. BM25 Reranking:**
- All vector search results are automatically reranked using BM25 algorithm
- Combines semantic similarity (vector search) with lexical relevance (BM25)
- Weighted scoring: 60% vector similarity + 40% BM25 relevance
- Significantly improves result accuracy and relevance

**3. Schema Format:**
Database schema is vectorized in this standardized format:
```
Database: [database_name]
Table: [table_name]
Table Description: [description]
Column: [column_name]
Datatype: [datatype]
primary key
Description: [column_description]
```

**4. Query Processing:**
- Synonym conversion: "field" → "column", "schema/db" → "database"
- Automatic prefix addition: "Table:", "Column:", "Database:", etc.
- Enhanced semantic understanding of database terminology

This ensures more accurate and relevant search results when exploring database metadata.

## Conversational Search Configuration

The knowledge base and metadata search now support follow-up questions with configurable conversation history limits. You can configure these in your `.env` file:

```bash
# Conversation history limits (number of message pairs to remember)
KNOWLEDGE_CONVERSATION_HISTORY_LIMIT=10   # For knowledge base search (default: 10)
METADATA_CONVERSATION_HISTORY_LIMIT=10    # For metadata search (default: 10)
```

**Features:**
- **Context Retention:** Both knowledge base and metadata search maintain conversation context for follow-up questions
- **Configurable Limits:** Control how many previous message pairs to remember for each search type
- **Automatic Cleanup:** History is automatically trimmed when limits are exceeded
- **Clear History:** Users can manually clear conversation history via the UI
- **Search Type Isolation:** Knowledge base and metadata search maintain separate conversation histories

### Migration from Direct ChromaDB

If you're migrating from a version that used direct ChromaDB integration:

1. **Backup existing data:** `python migrate_to_chromadb.py` includes backup functionality
2. **Start ChromaDB service:** Follow the setup instructions above
3. **Test migration:** Run `python test_chromadb_migration.py` to verify functionality
4. **Update configuration:** Ensure `CHROMADB_SERVICE_URL` in `config/config.py` points to your service

The migration maintains all existing data and functionality while providing improved architecture and scalability.

## Vector Database Architecture - ChromaDB REST API

The application uses a standalone ChromaDB service accessed via REST API for vector storage and similarity search. This architecture provides:

*   **Service Separation:** ChromaDB runs as a separate service, allowing for better scalability and maintenance
*   **REST API Access:** All vector operations (add, delete, search, etc.) are performed through HTTP REST API calls
*   **Microservices Architecture:** Clear separation between the main application and vector database service
*   **Enhanced Performance:** Dedicated service for vector operations with optimized resource allocation
*   **Better Error Handling:** Comprehensive error handling and logging for all vector operations

### Architecture Benefits:
- **Scalability:** Vector service can be scaled independently
- **Maintainability:** Clear separation of concerns between services
- **Reliability:** Robust error handling and automatic retry mechanisms
- **Flexibility:** Easy to replace or upgrade vector database service without affecting main application
- **Monitoring:** Dedicated logging and monitoring for vector operations

### ChromaDB Service:
The ChromaDB service (`chromadb_service/`) is a standalone Flask application that:
- Manages ChromaDB collections and embeddings
- Provides REST API endpoints for all vector operations
- Handles embedding generation using sentence-transformers
- Includes comprehensive error handling and logging
- Supports all required operations: insert, search, update, delete, and filtering

## Vector Database Filter System

The application uses a modernized filter system optimized for ChromaDB compatibility:

### ChromaDB Filter Architecture

**Filter Format:** All filters use native ChromaDB filter dictionaries for optimal performance.

```python
# ChromaDB filter format
filter_dict = {
    "table_name": "users",
    "$and": [
        {"schema_name": "public"},
        {"feedback_rating": {"$gte": 3}}
    ]
}
```

### LLM-Generated Filters

The `schema_vectorizer.py` now uses LLM to generate ChromaDB-compatible filters directly with enhanced rules:

**ENHANCED FILTERING RULES:**
- Extracts EXPLICITLY mentioned database/table/column names from queries
- Recognizes clear column names like "first_name", "user_id", "email"
- Uses smart logical operators: `$and` for specific columns within tables, `$or` for alternatives
- Does NOT infer generic terms like "customer information", "user data"
- Returns `null` if no explicit names are found

**LOGICAL OPERATOR INTELLIGENCE:**
- **$and**: For specific columns within specific tables (e.g., "column X FROM table Y")
- **$or**: For multiple alternatives (e.g., "table1 AND table2" or "column1 AND column2")
- **Single entity**: No operators needed for just table or just column

**DIRECT HIT OPTIMIZATION:**
- When LLM detects explicit table/column names, filter-based retrieval is used instead of vector search
- Automatic reranking skip for direct hits (improved performance)
- Raw schema metadata returned directly to LLM for comprehensive responses
- Simplified logic with no additional processing overhead

```python
# Valid examples (explicit names with correct operators):
"users table" → {"table": "users"}
"phone column from customers table" → {"$and": [{"table": "customers"}, {"column": "phone"}]}
"first_name and last_name columns" → {"$or": [{"column": "first_name"}, {"column": "last_name"}]}
"users table and orders table" → {"$or": [{"table": "users"}, {"table": "orders"}]}
"email and phone from users table" → {"$and": [{"table": "users"}, {"$or": [{"column": "email"}, {"column": "phone"}]}]}
"users table" → {"table": "users"}
"user_id column" → {"column": "user_id"}
"first_name and last_name columns" → {"$or": [{"column": "first_name"}, {"column": "last_name"}]}
"what does the column first_name and last_name contain" → {"$or": [{"column": "first_name"}, {"column": "last_name"}]}
"email, phone, address columns" → {"$or": [{"column": "email"}, {"column": "phone"}, {"column": "address"}]}

# Invalid examples (no explicit names):
"get me customer information" → null (generic term)
"column containing customer name" → null (no explicit column name)
```

### Available Filter Functions

Only essential filter functions remain:

- `create_rating_filter(rating)` - Feedback rating filter for feedback_manager.py
- `create_chunk_id_filter(chunk_id)` - Knowledge base chunk filter for knowledge_manager.py

### Migration Benefits

**Performance:** Native ChromaDB filters provide optimal query performance
**Simplicity:** Direct JSON filter usage without any conversion overhead
**Maintainability:** Minimal code surface area with only essential functions
**AI-Powered:** Intelligent filter generation based on natural language queries
**Type Safety:** All filters are strongly typed ChromaDB dictionaries

### Backend Integration

**Direct JSON Filtering:**
- `schema_vectorizer.py` - LLM creates ChromaDB filters from natural language queries
- `metadata_search_routes.py` - Handles direct hit detection and skips reranking for exact matches
- `feedback_manager.py` - Simple rating filters
- `knowledge_manager.py` - Simple chunk ID filters  
- `vector_db_routes.py` - Admin UI expects JSON filter format directly
- `vector_store.py` - Direct ChromaDB filter dictionaries only

The refactoring eliminates all backward compatibility and filter conversion logic, providing optimal performance with direct ChromaDB JSON filters.

## 🚀 Quick Start

### Prerequisites

- **Node.js** 20.19.0+ or 22.12.0+ (for frontend development)
- **Python** 3.8+ (for backend API)
- **Git** for version control

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd text2sql
   ```

2. **Backend Setup**
   ```bash
   # Create Python virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install Python dependencies
   pip install -r requirements.txt
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   
   # Install Node.js dependencies
   npm install
   ```

4. **Environment Configuration**
   ```bash
   # Copy and configure environment variables
   cp .env.example .env
   
   # Edit .env with your settings:
   # - AZURE_ENDPOINT, AZURE_MODEL_NAME, GITHUB_TOKEN (for Azure auth)
   # - DATABASE_URI, SECRET_KEY
   # - CHROMADB_SERVICE_URL (default: http://localhost:8001)
   ```

5. **Database Initialization**
   ```bash
   # Initialize database with default admin user
   python src/utils/init_db.py
   # Default admin credentials: admin/admin123 (change immediately!)
   ```

6. **ChromaDB Service Setup**
   ```bash
   cd chromadb_service
   pip install -r requirements.txt
   ```

## 🏃 Running the Application

### Development Mode (Recommended)

**Option 1: Automatic Startup (All Services)**
```bash
# Start all services with one command
./start_all_services.sh
```
This starts:
- ChromaDB service on port 8001
- Backend API server on port 5000
- Serves built frontend from `frontend/dist`

**Option 2: Manual Development Setup**

1. **Start ChromaDB Service**
   ```bash
   cd chromadb_service
   ./start_service.sh
   # Runs on http://localhost:8001
   ```

2. **Start Backend API Server**
   ```bash
   # From project root
   python app.py
   # Runs on http://localhost:5000
   ```

3. **Start Frontend Development Server** (for development)
   ```bash
   cd frontend
   npm run dev
   # Runs on http://localhost:3000 with hot reload
   # Automatically proxies API calls to http://localhost:5000
   ```

### Production Mode

1. **Build Frontend**
   ```bash
   cd frontend
   npm run build
   # Creates optimized build in frontend/dist/
   ```

2. **Start Services**
   ```bash
   # Start ChromaDB service
   cd chromadb_service && ./start_service.sh

   # Start backend (serves built frontend)
   python app.py
   ```

3. **Access Application**
   - **Production:** http://localhost:5000
   - **Development:** http://localhost:3000

### Access Points

| Service | Development | Production | Purpose |
|---------|------------|------------|---------|
| **Main Application** | http://localhost:3000 | http://localhost:5000 | Vue.js SPA with all features |
| **Backend API** | http://localhost:5000 | http://localhost:5000 | RESTful API endpoints |
| **ChromaDB Service** | http://localhost:8001 | http://localhost:8001 | Vector database operations |

## 🔧 Development Commands

### Frontend Commands

```bash
cd frontend

# Development server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run unit tests
npm run test:unit

# Run end-to-end tests
npm run test:e2e

# Lint and fix code
npm run lint

# Format code
npm run format

# Type checking
npm run type-check
```

### Backend Commands

```bash
# Start development server
python app.py

# Run API tests
python test_migration_comprehensive.py

# Initialize database
python src/utils/init_db.py

# Start MCP servers
./start_mcp_skill_server.sh
./start_mcp_data_mapping_server.sh
```

## 🧪 Testing

The application includes comprehensive testing suites:

### Frontend Testing
```bash
cd frontend

# Unit tests with Vitest
npm run test:unit

# E2E tests with Playwright
npm run test:e2e
```

### Backend Testing
```bash
# Comprehensive migration validation
python test_migration_comprehensive.py

# API endpoint testing
python test_basic_api.py
```

## 📁 Project Structure

```
text2sql/
├── 🎨 frontend/                 # Vue.js 3 SPA
│   ├── src/
│   │   ├── views/              # 23 Vue.js views (10 user + 13 admin)
│   │   ├── components/         # Reusable Vue components
│   │   ├── stores/             # Pinia state management
│   │   ├── services/           # API service layer
│   │   ├── router/             # Vue Router configuration
│   │   └── types/              # TypeScript type definitions
│   ├── dist/                   # Built frontend (production)
│   ├── package.json            # Node.js dependencies
│   ├── vite.config.ts          # Vite build configuration
│   └── tailwind.config.js      # Tailwind CSS configuration
├── 🚀 src/                     # Backend API source
│   ├── api/                    # API v1 endpoints (/api/v1/)
│   ├── routes/                 # Admin API routes (/api/v1/admin/)
│   ├── models/                 # Business logic and data models
│   ├── utils/                  # Helper modules (DB, AI client, auth)
│   ├── middleware/             # CORS, error handling, JWT auth
│   └── services/               # Background services (MCP servers)
├── 📊 chromadb_service/        # Standalone ChromaDB REST API
│   ├── app.py                  # ChromaDB service Flask app
│   ├── requirements.txt        # Service dependencies
│   └── start_service.sh        # Service startup script
├── 📝 config/                  # Configuration files
├── 📋 logs/                    # Application logs
├── 📄 uploads/                 # Knowledge base documents
├── 🗄️ *.db                     # SQLite databases
├── app.py                      # Main Flask API application
├── requirements.txt            # Python dependencies
└── start_all_services.sh       # Complete application startup
```

## Service Management & Troubleshooting

### ChromaDB Service Management

**Starting the Service:**
```bash
cd chromadb_service
./start_service.sh
```

**Stopping the Service:**
```bash
# Find the process ID
ps aux | grep "python app.py"
# Kill the process
kill <PID>
```

**Service Health Check:**
```bash
curl http://localhost:8001/health
```

**View Service Logs:**
```bash
tail -f chromadb_service/service.log
```

### Common Issues

**1. ChromaDB Service Not Starting:**
- Check if port 8001 is available: `netstat -tlnp | grep 8001`
- Verify Python environment and dependencies
- Check service logs for error messages

**2. Connection Refused Errors:**
- Ensure ChromaDB service is running before starting main application
- Verify `CHROMADB_SERVICE_URL` in config matches service address
- Check firewall settings if running on different machines

**3. Vector Search Not Working:**
- Verify collections exist: Check admin vector DB management UI

## MCP Skill Library Server Setup

The MCP Skill Library Server provides enterprise skill management and can be integrated with agent mode for enhanced task execution capabilities.

### Quick Start

**1. Initialize Skill Database:**
```bash
# Load sample skills into the database
python3 init_skill_library_db.py
```

**2. Start MCP Skill Server:**
```bash
# Start the skill library server (HTTP/SSE)
./start_mcp_skill_server.sh
```

**3. Configure in Agent Mode:**
Add the MCP Skill Server to your agent configuration:
- Server Type: HTTP
- URL: `http://localhost:8002`
- Name: `skill-library`

### Skill Management

**Access Admin Interface:**
Navigate to **Admin → Skill Library** in the web interface to:
- View and search existing skills
- Create new skills with detailed steps
- Import skills from JSON files
- Manage skill categories and versions
- View skill library statistics

**Skill Structure:**
Each skill contains:
- **Name & Description:** Clear identification and purpose
- **Category:** Domain classification (data engineering, DevOps, etc.)
- **Prerequisites:** Required knowledge, tools, or access
- **Technical Steps:** Detailed step-by-step instructions
- **Examples:** Usage scenarios and sample implementations
- **Tags:** Keywords for better searchability

**Sample Skills Included:**
- Database Schema Analysis
- ETL Pipeline Development  
- Data Quality Assessment
- API Integration Development
- Automated Report Generation
- Database Performance Optimization
- Data Migration Planning
- Real-time Data Streaming Setup
- Automated Testing Framework
- Security Audit and Compliance

### Integration with Agent Mode

When the MCP Skill Server is configured in agent mode, LLMs can:

1. **Search Skills:** Use natural language to find relevant skills
   ```
   Agent: "How do I optimize database performance?"
   Skill Library: Returns "Database Performance Optimization" skill
   ```

2. **Get Detailed Steps:** Retrieve comprehensive technical instructions
   ```
   Agent: "Get details for skill ID abc123"
   Skill Library: Returns complete skill with prerequisites and steps
   ```

3. **Browse Categories:** Explore skills by domain expertise
   ```
   Agent: "List all data engineering skills"
   Skill Library: Returns filtered skills by category
   ```

4. **Execute with Context:** Use skill instructions to carry out complex tasks through other MCP servers

### Advanced Configuration

**Environment Variables:**
```bash
# Skill server configuration
export MCP_SKILL_HOST=localhost
export MCP_SKILL_PORT=8002
export MCP_SKILL_DEBUG=false

# Vector search requires ChromaDB service
export CHROMADB_SERVICE_URL=http://localhost:8001
```

**Custom Skill Import:**
Create a JSON file with your enterprise skills:
```json
{
  "skills": [
    {
      "name": "Custom Enterprise Skill",
      "description": "Description of the skill",
      "category": "data_engineering",
      "steps": ["Step 1", "Step 2", "Step 3"],
      "tags": ["custom", "enterprise"],
      "prerequisites": ["Requirement 1"],
      "examples": ["Example usage"]
    }
  ]
}
```

Then import via the admin interface or API endpoint.

### API Integration

The MCP Skill Server provides a REST API for external integration:

**Available Endpoints:**
- `GET /health` - Health check
- `POST /mcp/initialize` - MCP protocol initialization
- `POST /mcp/tools/list` - List available tools
- `POST /mcp/tools/call` - Execute skill operations

**MCP Tools:**
- `search_skills` - Search skills with natural language
- `get_skill_details` - Get complete skill information
- `list_categories` - List skill categories with counts
- `get_skill_stats` - Get skill library statistics
- Ensure embeddings are being generated properly
- Check ChromaDB service logs for embedding errors

**4. Performance Issues:**
- Monitor ChromaDB service resource usage
- Consider increasing service timeout settings
- Check embedding model performance (all-MiniLM-L6-v2 is lightweight)

### Development Tips

- Use `DEBUG=True` in ChromaDB service config during development
- Monitor both application and service logs simultaneously
- Test vector operations using the admin interface before implementing new features
- Use the migration test script to verify functionality after changes

## 🔒 Security Highlights

The modern Vue.js + Flask API architecture includes comprehensive security measures:

### Authentication & Authorization
- **JWT Authentication** - Stateless token-based authentication with automatic refresh
- **Role-Based Access Control (RBAC)** - Granular permissions for user and admin operations
- **Secure Password Management** - bcrypt hashing with password reset via email tokens
- **Session Security** - Secure cookie settings with HttpOnly and SameSite attributes

### API Security
- **CORS Configuration** - Proper cross-origin resource sharing setup for secure API access
- **Request Validation** - Input sanitization and validation across all endpoints
- **Rate Limiting** - Protection against abuse on sensitive endpoints
- **Error Handling** - Structured error responses without sensitive information exposure

### Application Security
- **CSRF Protection** - Cross-Site Request Forgery protection for state-changing operations
- **Security Headers** - CSP, X-Frame-Options, X-Content-Type-Options for client protection
- **Audit Logging** - Comprehensive activity tracking for compliance and monitoring
- **Environment Configuration** - Secure handling of secrets and configuration management

### Production Recommendations
- **HTTPS Required** - Use HTTPS in production for encrypted communication
- **Environment Variables** - Store sensitive configuration in environment variables
- **Debug Mode** - Set `DEBUG=False` in production environments
- **Database Security** - Use production-grade databases with proper access controls
- **Regular Updates** - Keep dependencies updated and monitor security advisories

## Contributing

Contributions are welcome! Please follow standard fork/branch/pull request workflow. Open an issue to discuss significant changes first.

## License

[MIT License]