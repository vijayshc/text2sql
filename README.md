# Text2SQL Assistant

A## Sensitive Tool Confirmation:** Requires user approval before executing potentially sensitive operations like shell commands.
  
  This feature adds an intermediate confirmation dialog whenever the agent attempts to run sensitive tools (e.g., `run_bash_shell`). Users will receive a popup showing the tool name and arguments, and must confirm or cancel execution. If canceled, the operation is aborted and the agent stops processing further.

## MCP Server Management

The application now supports managing multiple Model Context Protocol (MCP) servers:

* **Server Types:** Support for both stdio (command-line process) and HTTP/SSE servers
* **Admin Interface:** Add, configure, start/stop, and monitor MCP servers
* **Auto-Selection:** The system can intelligently select the most appropriate MCP server for each user query
* **Server State Persistence:** MCP server state (running/stopped) is preserved across application restarts
* **Tool Discovery:** View available tools for each MCP server through the admin interface
* **Conversation History for Follow-up Questions:** Agent chat now maintains conversation context, allowing users to ask follow-up questions with the context of previous exchangesb application that translates natural language questions into SQL queries, executes them against a database, and displays the results. It uses AI (Azure AI Inference) and incorporates feedback mechanisms to improve accuracy over time.

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