# Text2SQL Assistant

This project is a web application designed to bridge the gap between natural language and databases. It allows users to ask questions in plain English, converts those questions into SQL queries using an AI model (Azure AI Inference), executes them against a database, and presents the results in a user-friendly interface. The system incorporates feedback mechanisms and advanced techniques to continuously improve the accuracy of the generated SQL.

## Core Features

*   **Natural Language to SQL:** Converts user questions into executable SQL queries.
*   **Database Interaction:** Executes generated SQL against a configured SQLite database (`text2sql.db`) and displays results.
*   **Schema Awareness:** Leverages detailed schema information (`config/data/schema.json`), including table/column descriptions and relationships (`config/data/condition.json`), to generate contextually accurate queries.
*   **Workspace Support:** Organizes database tables into logical workspaces for better context management (defined in `app.py`).
*   **Table Mentions:** Allows users to explicitly reference tables using `@tableName` syntax within their queries for precision.
*   **Interactive UI:** Web interface built with Flask, Bootstrap 5, and modern JavaScript for a responsive user experience.
*   **Results Display:** Presents query results in a sortable, filterable table (using DataTables) and offers options for data visualization (planned).
*   **SQL & Explanation:** Shows the generated SQL query (with enhanced syntax highlighting) and a natural language explanation provided by the AI model.
*   **Detailed Processing Steps:** Provides transparency by displaying the intermediate steps taken during query generation (e.g., intent detection, table selection, column pruning, SQL generation).
*   **Schema Viewer:** Enables users to browse the database schema (tables, columns, types, descriptions) directly within the application, with planned enhancements for search and relationship visualization.
*   **User Feedback System:** Collects user ratings (thumbs up/down) and categorized reasons for inaccuracies, feeding this data back to improve future performance.
*   **Sample Management:** Maintains a library of curated query examples and automatically incorporates successful user queries (with positive feedback) as samples. Includes a dedicated UI for managing these samples.
*   **Two-Stage Similarity Search:** Employs vector embeddings and cross-encoder reranking to find the most relevant past queries or samples, providing valuable context (few-shot examples) to the AI model for better accuracy.
*   **SQL Self-Correction:** Attempts to automatically correct SQL queries that fail execution by feeding the database error back to the AI model for revision.
*   **Robust Error Handling:** Implements custom error pages and provides user-friendly error messages in the UI when issues occur.
*   **Configuration:** Flexible configuration via environment variables (`.env` file) for Azure AI, database connections, and application settings.

## Tech Stack

*   **Backend:** Python 3.x, Flask
*   **AI Model:** Azure AI Inference Service (configurable model, e.g., Phi-3) via REST API
*   **LLM Interaction:** Custom client (`src/utils/azure_client.py`, `src/utils/llm_engine.py`)
*   **Database:** SQLite (default), SQLAlchemy (ORM)
*   **Vector Embeddings:** Sentence-Transformers library
*   **Semantic Search:** Vector similarity search + Cross-Encoder models for reranking
*   **Frontend:** HTML5, CSS3, JavaScript (ES6+), Bootstrap 5, jQuery, DataTables.js
*   **Environment Management:** `python-dotenv`
*   **Logging:** Python's built-in `logging` module

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd text2sql
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    # Note: Sentence Transformers and Cross-Encoders might download models on first run.
    ```

4.  **Configure Environment Variables:**
    Create a `.env` file in the project root directory. Copy the contents of `.env.example` (if provided) or create it from scratch. Add the following variables, replacing placeholder values:
    ```env
    # Azure AI Configuration
    AZURE_ENDPOINT="<your_azure_ai_inference_endpoint>"
    AZURE_MODEL_NAME="<your_deployed_model_name>" # e.g., Phi-3-small-8k-instruct
    GITHUB_TOKEN="<your_github_token_for_azure_auth>" # Or configure other Azure credential methods in azure_client.py

    # Database Configuration (default is SQLite in project root)
    DATABASE_URI="sqlite:///text2sql.db"

    # Flask Settings
    SECRET_KEY="<generate_a_strong_random_secret_key>" # Important for session security
    DEBUG="True" # Set to False for production
    FLASK_ENV="development" # Set to production for production

    # Model Configuration (Optional - see config/config.py for defaults)
    # MAX_TOKENS=2048
    # TEMPERATURE=0.5
    # TOP_P=0.95
    ```
    *   Refer to `config/config.py` for all configurable environment variables and their defaults.
    *   Ensure the credentials used for Azure AI authentication have the necessary permissions.

5.  **Initialize the Database:**
    Run the initialization script. This creates the SQLite database file (`text2sql.db`), sets up the necessary tables (including for feedback and samples), and populates it with initial schema data and potentially sample table data.
    ```bash
    python src/utils/init_db.py
    ```
    *   Review `init_db.py` if you need to load different initial data.

## Running the Application

1.  **Start the Flask development server:**
    ```bash
    python app.py
    ```
    Or use the provided restart script (ensure it has execute permissions: `chmod +x restart.sh`):
    ```bash
    ./restart.sh
    ```
    This script typically stops any existing instance, clears caches (if implemented), and restarts the server.

2.  Open your web browser and navigate to `http://127.0.0.1:5000` (or the address/port provided by Flask in the console).

## Project Structure

```
text2sql/
├── app.py              # Main Flask application: routing, request handling
├── requirements.txt    # Python dependencies
├── restart.sh          # Utility script for restarting the server
├── text2sql.db         # SQLite database file (created by init_db.py)
├── .env                # Environment variables (sensitive, DO NOT COMMIT)
├── .gitignore          # Specifies intentionally untracked files
├── config/
│   ├── config.py       # Loads configuration from .env and defaults
│   └── data/
│       ├── schema.json # Defines database schema structure, descriptions for AI
│       └── condition.json # Optional pre-defined join conditions between tables
├── logs/               # Log files (created automatically if logging is enabled)
│   ├── error.log       # Application error logs
│   ├── queries.log     # Logs of generated/executed SQL queries
│   └── text2sql.log    # General application activity logs
├── src/                # Core source code
│   ├── agents/         # AI Agents for specific sub-tasks
│   │   ├── __init__.py
│   │   ├── column_agent.py    # Selects relevant columns based on query context
│   │   ├── intent_agent.py    # Determines user's goal (data retrieval, schema info, etc.)
│   │   └── table_agent.py     # Identifies relevant tables for the query
│   ├── models/         # High-level business logic
│   │   ├── __init__.py
│   │   └── sql_generator.py   # Orchestrates the Text-to-SQL pipeline using agents and utils
│   └── utils/          # Utility modules and helper functions
│       ├── __init__.py
│       ├── azure_client.py    # Handles communication with Azure AI Inference API
│       ├── csv_to_schema.py   # Script to help generate schema.json from CSV (manual refinement needed)
│       ├── database.py        # Database connection and session management (SQLAlchemy)
│       ├── feedback_manager.py # Manages storing/retrieving feedback and samples, handles embeddings
│       ├── init_db.py         # Database schema creation and initial data loading
│       ├── llm_engine.py      # Centralizes interaction logic with the LLM (prompt formatting, etc.)
│       └── schema_manager.py  # Loads, parses, and provides access to schema information
├── static/             # Frontend assets (served directly by Flask/webserver)
│   ├── css/
│   │   └── styles.css  # Custom application stylesheets
│   └── js/             # Modularized JavaScript files
│       ├── core.js             # Core frontend initialization, event listeners
│       ├── feedback.js         # Handles sending feedback (thumbs up/down, reasons)
│       ├── query-handler.js    # Manages query submission via AJAX, progress updates
│       ├── results-display.js  # Renders results table, SQL, explanation, steps
│       ├── samples.js          # JavaScript for the sample management page
│       ├── schema-manager.js   # Handles fetching and displaying schema in the modal
│       ├── table-mentions.js   # Implements the @mention functionality in the query input
│       └── ui-utils.js         # Common UI helper functions (e.g., showing alerts)
└── templates/          # HTML templates (rendered by Flask using Jinja2)
    ├── index.html      # Main application page template
    ├── samples.html    # Sample management page template
    ├── 404.html        # Custom "Not Found" error page
    └── 500.html        # Custom "Internal Server Error" page
    └── base.html       # Base template extended by other pages (optional)
```

## Advanced Features & Concepts

### Feedback Loop

The feedback system is crucial for improvement:
1.  **Collection:** User provides thumbs up/down. Thumbs down can include optional categorized reasons (e.g., "Incorrect tables," "Wrong calculation").
2.  **Storage:** Query text, generated SQL, user rating, reason (if provided), and execution metadata are stored in the `feedback` table.
3.  **Embedding:** Query text is converted into a vector embedding using Sentence-Transformers.
4.  **Retrieval (Similarity Search):** When a new query arrives, the `FeedbackManager` searches for similar past queries (especially positively rated ones) using the two-stage search.
5.  **Contextual Improvement:** These relevant examples are included in the prompt sent to the AI model, guiding it to generate better SQL for similar requests.

### Sample Management

Provides a way to curate high-quality examples:
*   **Manual Curation:** Users can add known good question/SQL pairs via the `/samples` page.
*   **Automatic Inclusion:** Positively rated user feedback can be configured to automatically become part of the sample set used in similarity searches.
*   **Management UI:** Allows viewing, searching, filtering, and editing/deleting samples.

### Two-Stage Similarity Search

Improves the relevance of examples shown to the AI:
1.  **Candidate Retrieval (Vector Search):** Quickly finds a larger set (e.g., top 10) of potentially relevant queries/samples based on vector similarity (cosine similarity on embeddings). This is fast but less precise.
2.  **Reranking (Cross-Encoder):** A more computationally intensive but accurate cross-encoder model compares the input query directly against each candidate from stage 1. It outputs a relevance score.
3.  **Selection:** The system selects the top N (e.g., top 2) candidates with the highest reranking scores (above a certain threshold) to use as few-shot examples in the prompt. This ensures only highly relevant examples influence the AI.

### SQL Self-Correction Attempt

When a generated SQL query fails during execution:
1.  The database error message is captured.
2.  The `SQLGenerationManager` can trigger a second call to the `AzureAIClient`.
3.  This second call includes the original query, the failed SQL, *and* the database error message, prompting the AI to fix the query.
4.  If the revised query is generated, the system attempts to execute it. (Note: This is a basic implementation and may not solve all errors).

## Configuration Details

*   **Application Settings:** Managed in `config/config.py`, primarily loaded from environment variables (`.env`). See `config.py` for defaults and descriptions.
*   **Database Schema (`config/data/schema.json`):** This is critical for AI accuracy. It must accurately reflect the *actual* database structure. Include detailed descriptions for tables and columns, specifying data types, units, common values, and relationships where possible. Use `src/utils/csv_to_schema.py` as a starting point, but **manual refinement is essential**.
*   **Join Conditions (`config/data/condition.json`):** Optionally define explicit join paths between tables. This helps the AI construct correct JOIN clauses, especially in complex schemas.
*   **Logging:** Configured in `config/config.py`. Logs are written to the `logs/` directory by default. Log levels can be adjusted via environment variables.

## Contributing

Contributions are welcome! Please adhere to the existing code style and project structure. Consider opening an issue first to discuss proposed changes.

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/YourFeature`).
3.  Commit your changes (`git commit -m 'Add some feature'`).
4.  Push to the branch (`git push origin feature/YourFeature`).
5.  Open a Pull Request.

## License

[Specify License Here - e.g., MIT License, Apache 2.0]