# Text2SQL Assistant

A## Sensitive Tool Confirmation:** Requires user approval before executing potentially sensitive operations like shell commands.
  
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
*   **Knowledge Base Q&A:** Answers questions based on uploaded documents or directly pasted text using vector search.
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

## Tech Stack

*   **Backend:** Python, Flask, SQLAlchemy
*   **AI:** Azure AI Inference Service, Sentence-Transformers, OpenRouter
*   **Frontend:** HTML, CSS, JavaScript, Bootstrap 5, jQuery
*   **Database:** SQLite (default)
*   **Vector Database:** ChromaDB REST API Service (for embeddings and similarity search)
*   **MCP Support:** Model Context Protocol support for both stdio and HTTP servers

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

## Setup and Installation

1.  **Clone:** `git clone <repository-url> && cd text2sql`
2.  **Environment:** `python -m venv venv && source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
3.  **Install:** `pip install -r requirements.txt`
4.  **Configure:** Create a `.env` file (copy `.env.example` if available) and fill in `AZURE_ENDPOINT`, `AZURE_MODEL_NAME`, `GITHUB_TOKEN` (for Azure auth), `DATABASE_URI`, and `SECRET_KEY`. See `config/config.py` for more options.
5.  **Initialize DB:** `python src/utils/init_db.py` (Creates DB and default admin user: admin/admin123 - **change immediately!**)
6.  **Setup ChromaDB Service:** 
   - Navigate to `chromadb_service/` directory
   - Install service dependencies: `pip install -r requirements.txt`
   - Start the ChromaDB service: `chmod +x start_service.sh && ./start_service.sh`
   - The service will run on `http://localhost:8001` by default

## Running the Application

1.  **Start ChromaDB Service:** `cd chromadb_service && ./start_service.sh` (runs on port 8001)
2.  **Start Main Application:** `python app.py` or `./restart.sh` (runs on port 5000)
3.  **Access:** Open `http://127.0.0.1:5000` in your browser.
4.  **Login:** Use the default admin credentials and change the password via the admin panel.

**Important:** The ChromaDB service must be running before starting the main application, as all vector operations depend on it.

## Project Structure Overview

```
text2sql/
├── app.py              # Main Flask application
├── requirements.txt    # Dependencies
├── .env                # Environment variables (DO NOT COMMIT)
├── config/             # Configuration files (app settings, schema)
├── src/                # Core source code
│   ├── agents/         # AI agents for sub-tasks
│   ├── models/         # Business logic (SQL generation, User model)
│   ├── routes/         # Flask Blueprints for different features
│   ├── static/         # CSS, JavaScript files
│   ├── templates/      # HTML templates
│   └── utils/          # Helper modules (DB, AI client, auth, etc.)
├── chromadb_service/   # Standalone ChromaDB REST API service
│   ├── app.py          # ChromaDB service Flask application
│   ├── requirements.txt # Service-specific dependencies
│   ├── config.py       # Service configuration
│   ├── start_service.sh # Service startup script
│   └── README.md       # Service documentation
├── logs/               # Log files
├── uploads/            # Uploaded knowledge base documents
└── text2sql.db         # Default SQLite database
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

## Security Highlights

*   Secure password hashing (bcrypt) and reset mechanism.
*   Role-Based Access Control (RBAC) for authorization.
*   CSRF protection and standard security headers (CSP, X-Frame-Options, etc.).
*   Rate limiting on sensitive endpoints.
*   Audit logging for tracking actions.
*   **Important:** Set `DEBUG=False` and use HTTPS in production.

## Contributing

Contributions are welcome! Please follow standard fork/branch/pull request workflow. Open an issue to discuss significant changes first.

## License

[MIT License]