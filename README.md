# Text2SQL Assistant

This project is a web application that converts natural language questions into SQL queries and executes them against a configured database. It uses an AI model (specifically configured for Azure AI Inference) to understand the user's intent and generate the appropriate SQL.

## Features

* **Natural Language to SQL:** Converts plain English questions into executable SQL queries.
* **Database Interaction:** Executes generated SQL against a SQLite database (`text2sql.db`) and displays results.
* **Schema Awareness:** Uses schema information from `config/data/schema.json` to generate accurate queries.
* **Workspace Support:** Allows organizing tables into different workspaces (defined in `app.py`).
* **Table Mentions:** Users can use `@` to mention specific tables in their query.
* **Interactive UI:** Web interface built with Flask, Bootstrap, and JavaScript.
* **Results Display:** Shows query results in a sortable and filterable table using DataTables.
* **SQL & Explanation:** Displays the generated SQL query and an explanation from the AI model.
* **Processing Steps:** Shows the intermediate steps taken by the backend to generate the query.
* **Schema Viewer:** Allows users to browse the database schema within the application.
* **User Feedback System:** Collects user feedback (thumbs up/down) on generated SQL queries for continuous improvement.
* **Sample Management:** Maintains a library of sample queries that can be used as examples for similar queries.
* **Two-Stage Similarity Search:** Uses vector embeddings and reranking to find similar previous queries for improved results.
* **Error Handling:** Custom error pages and robust error handling throughout the application.

## Tech Stack

* **Backend:** Python, Flask
* **AI Model:** Azure AI Inference Service (configured via `config/config.py` and used through `src/utils/llm_engine.py`)
* **Database:** SQLite (default), SQLAlchemy for database interactions
* **Vector Embeddings:** Sentence-Transformers for generating query embeddings
* **Semantic Search:** Two-stage similarity search with reranking using cross-encoder models
* **Frontend:** HTML, CSS, JavaScript, Bootstrap 5, jQuery, DataTables
* **Environment Management:** `python-dotenv`

## Setup and Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd text2sql
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   Create a `.env` file in the project root directory. Add the following variables, replacing the placeholder values with your actual credentials and settings:
   ```env
   # Azure AI Configuration
   AZURE_ENDPOINT="<your_azure_ai_inference_endpoint>"
   AZURE_MODEL_NAME="<your_deployed_model_name>" # e.g., Phi-3-small-8k-instruct
   GITHUB_TOKEN="<your_github_token_for_azure_auth>" # Or other Azure credential method

   # Database Configuration (default is SQLite in project root)
   # DATABASE_URI="sqlite:///text2sql.db"

   # Flask Settings
   SECRET_KEY="<a_strong_random_secret_key>"
   DEBUG="True" # Set to False for production
   FLASK_ENV="development" # Set to production for production

   # Model Configuration (Optional)
   # MAX_TOKENS=2000
   # TEMPERATURE=0.7
   ```
   * Refer to `config/config.py` for all possible environment variables.
   * Ensure the `GITHUB_TOKEN` has appropriate permissions if using it for Azure AI authentication.

5. **Initialize the Database:**
   Run the initialization script to create the SQLite database (`text2sql.db`) and populate it with sample data:
   ```bash
   python src/utils/init_db.py
   ```

## Running the Application

1. **Start the Flask development server:**
   ```bash
   python app.py
   ```
   Or use the provided restart script (ensure it has execute permissions: `chmod +x restart.sh`):
   ```bash
   ./restart.sh
   ```

2. Open your web browser and navigate to `http://127.0.0.1:5000` (or the address provided by Flask).

## Project Structure

```
├── app.py              # Main Flask application file
├── requirements.txt    # Python dependencies
├── restart.sh          # Script to stop/clear cache/restart the app
├── text2sql.db         # SQLite database file (created by init_db.py)
├── config/
│   ├── config.py       # Application configuration, reads .env
│   └── data/
│       ├── schema.json # Defines database schema for the AI model
│       └── condition.json # Optional pre-defined join conditions
├── logs/               # Log files (created automatically)
│   ├── error.log       # Error logs
│   ├── queries.log     # SQL query logs
│   └── text2sql.log    # General application logs
├── src/                # Source code
│   ├── agents/         # Specialized agents for different aspects of query processing
│   │   ├── column_agent.py    # Selects relevant columns
│   │   ├── intent_agent.py    # Determines user intent
│   │   └── table_agent.py     # Identifies relevant tables
│   ├── models/
│   │   └── sql_generator.py   # Coordinates the SQL generation pipeline
│   └── utils/
│       ├── azure_client.py    # Client for Azure AI service
│       ├── csv_to_schema.py   # Utility for converting CSV to schema.json
│       ├── database.py        # Database connection management
│       ├── feedback_manager.py # Manages user feedback and samples
│       ├── init_db.py         # Database initialization
│       ├── llm_engine.py      # Centralized LLM interaction
│       └── schema_manager.py  # Manages database schema information
├── static/             # Frontend assets
│   ├── css/
│   │   └── styles.css  # Custom stylesheets
│   └── js/             # Modularized JavaScript
│       ├── core.js             # Core initialization
│       ├── feedback.js         # Feedback handling
│       ├── query-handler.js    # Query submission and processing
│       ├── results-display.js  # Results visualization
│       ├── samples.js          # Sample management
│       ├── schema-manager.js   # Schema display
│       ├── table-mentions.js   # Table mention functionality
│       └── ui-utils.js         # UI utilities
└── templates/          # HTML templates for Flask
    ├── index.html      # Main application page
    ├── samples.html    # Sample management page
    ├── 404.html        # Custom 404 error page
    └── 500.html        # Custom 500 error page
```

## Advanced Features

### Feedback System

The application includes a comprehensive feedback system that:
* Collects user feedback (thumbs up/down) on generated SQL queries
* Stores query text, SQL, and metadata in the database
* Generates embeddings for each query for similarity search
* Uses feedback data to improve future query generation

### Sample Management

The sample management system allows:
* Adding manually curated examples of natural language queries and their SQL equivalents
* Viewing and editing existing samples
* Automatic inclusion of positive user feedback as samples
* Filtering and searching through samples

### Two-Stage Similarity Search

When generating SQL, the application uses a sophisticated similarity search approach:
1. **First stage:** Vector search using sentence embeddings to find top 10 candidate matches
2. **Second stage:** Reranking using a cross-encoder model to select the top 2 most semantically similar queries
3. Filtering out any candidates with negative reranking scores (indicating poor relevance)
4. Using only the most relevant examples when generating new SQL queries

## Configuration

* **Application Settings:** Managed in `config/config.py`, primarily loaded from environment variables defined in the `.env` file.
* **Database Schema:** The structure of the database tables, columns, and descriptions used by the AI model is defined in `config/data/schema.json`. This file needs to be kept in sync with the actual database schema. The `src/utils/csv_to_schema.py` script can help generate this from a CSV file, but manual refinement is often necessary.
* **Logging:** Configured within `config/config.py`, logs are written to the `logs/` directory.

## Contributing

Contributions to the Text2SQL Assistant are welcome! Please ensure you follow the existing code style and structure when submitting pull requests.

## License

[Specify license information here]