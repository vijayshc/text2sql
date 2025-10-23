# Text2SQL Assistant

A comprehensive AI-powered database query assistant with advanced features for enterprise environments.

## Key Features

* **Natural Language to SQL:** Converts English questions to SQL with schema awareness
* **Knowledge Base Q&A:** Vector search-based document Q&A with conversational support
* **Database Metadata Search:** Enhanced schema exploration with BM25 reranking
* **Agent Mode:** Multi-server AI agent with MCP protocol support
* **AI Data Mapping Analyst:** Advanced data mapping and lineage analysis
* **MCP Skill Library:** Enterprise skill repository with semantic search
* **Audit Logging:** Comprehensive audit trails for compliance
* **Security:** RBAC, CSRF protection, rate limiting, and sensitive tool confirmation
* **Admin Dashboard:** User management, system monitoring, and configuration

## Tech Stack

* **Backend:** Python, Flask, SQLAlchemy
* **AI:** Azure AI Inference Service, Sentence-Transformers, OpenRouter
* **Frontend:** HTML, CSS, JavaScript, Bootstrap 5, jQuery
* **Database:** SQLite (default), ChromaDB for vector storage
* **MCP Support:** Model Context Protocol for stdio and HTTP servers

## Quick Start

1. **Clone Repository:**
   ```bash
   git clone <repository-url> && cd text2sql
   ```

2. **Setup Environment:**
   ```bash
   python -m venv venv && source venv/bin/activate  # Linux/Mac
   # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. **Configuration:**
   - Copy `.env.example` to `.env`
   - Set required variables: `AZURE_ENDPOINT`, `AZURE_MODEL_NAME`, `GITHUB_TOKEN`, `DATABASE_URI`, `SECRET_KEY`

4. **Initialize Database:**
   ```bash
   python src/utils/init_db.py
   ```

5. **Start Services:**
   ```bash
   # Start ChromaDB service
   cd chromadb_service && ./start_service.sh

   # Start main application
   cd .. && python app.py
   ```

6. **Access Application:**
   - Open `http://127.0.0.1:5000`
   - Default admin: `admin/admin123` (change immediately!)

## Architecture Overview

```
text2sql/
├── app.py                    # Main Flask application
├── config/                   # Configuration files
├── src/                      # Core source code
│   ├── agents/              # AI agents for sub-tasks
│   ├── models/              # Business logic
│   ├── routes/              # Flask Blueprints
│   ├── services/            # MCP servers and orchestrators
│   ├── static/              # CSS, JavaScript files
│   └── utils/               # Helper modules
├── chromadb_service/        # Vector database service
├── templates/               # HTML templates
├── logs/                    # Application logs
├── uploads/                 # Knowledge base documents
└── text2sql.db             # SQLite database
```

## Advanced Features

### AI Data Mapping Analyst
Advanced enterprise-grade system for data warehousing and data mart development:
- Intelligent column mapping with AI-powered analysis
- Graph-based join path discovery using NetworkX
- Semantic column matching across different naming conventions
- ETL transformation logic generation
- New table structure proposals

### MCP Skill Library Server
Enterprise skill repository with:
- Vector search for natural language queries
- Dynamic category organization
- Step-by-step technical guidance
- Admin interface for skill management
- HTTP/SSE interface for MCP integration

### Agent Mode
Multi-server AI agent capabilities:
- Automatic MCP server selection
- Tool execution with user confirmation
- Streaming responses and conversation context
- Integration with skill library and data mapping tools

### Enhanced Search Features
- **Metadata Search:** BM25 reranking with query reformatting
- **Knowledge Base:** Conversational Q&A with vector similarity
- **Schema Exploration:** Comprehensive database metadata analysis

## Configuration

### Environment Variables
```bash
# AI Configuration
AZURE_ENDPOINT=your-azure-endpoint
AZURE_MODEL_NAME=your-model-name
MESSAGE_FORMAT=openai  # or llama

# Database
DATABASE_URI=sqlite:///text2sql.db

# Security
SECRET_KEY=your-secret-key
DEBUG=False

# Services
CHROMADB_SERVICE_URL=http://localhost:8001

# Conversation Limits
KNOWLEDGE_CONVERSATION_HISTORY_LIMIT=10
METADATA_CONVERSATION_HISTORY_LIMIT=10
```

### LDAP Authentication (Optional)
```bash
AUTH_PROVIDER=ldap
LDAP_SERVER_URI=ldaps://ad.example.com
LDAP_USE_SSL=true
LDAP_USER_FILTER_TEMPLATE=(sAMAccountName={username})
LDAP_ALLOWED_GROUP_DN=CN=Text2SQL Users,OU=Groups,DC=example,DC=com
```

## Service Management

### ChromaDB Service
```bash
# Start service
cd chromadb_service && ./start_service.sh

# Health check
curl http://localhost:8001/health

# View logs
tail -f chromadb_service/service.log
```

### MCP Servers
```bash
# Skill Library Server
./start_mcp_skill_server.sh

# Data Mapping Server
python -m src.services.mcp_data_mapping_server --host 0.0.0.0 --port 8003
```

## Security

* Secure password hashing with bcrypt
* Role-Based Access Control (RBAC)
* CSRF protection and security headers
* Rate limiting on sensitive endpoints
* Audit logging for compliance
* Sensitive tool confirmation dialogs

## Contributing

Contributions welcome! Please follow standard fork/branch/pull request workflow.

## License

MIT License
