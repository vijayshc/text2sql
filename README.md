# Text2SQL Assistant

This project is a web application that converts natural language questions into SQL queries and executes them against a configured database. It uses an AI model (specifically configured for Azure AI Inference) to understand the user's intent and generate the appropriate SQL.

## Features

*   **Natural Language to SQL:** Converts plain English questions into executable SQL queries.
*   **Database Interaction:** Executes generated SQL against a SQLite database ([`text2sql.db`](text2sql.db)) and displays results.
*   **Schema Awareness:** Uses schema information from [`config/data/schema.json`](config/data/schema.json) to generate accurate queries.
*   **Workspace Support:** Allows organizing tables into different workspaces (defined in [`app.py`](app.py)).
*   **Table Mentions:** Users can use `@` to mention specific tables in their query ([`static/js/main.js`](static/js/main.js)).
*   **Interactive UI:** Web interface built with Flask, Bootstrap, and JavaScript ([`templates/index.html`](templates/index.html), [`static/css/styles.css`](static/css/styles.css), [`static/js/main.js`](static/js/main.js)).
*   **Results Display:** Shows query results in a sortable and filterable table using DataTables.
*   **SQL & Explanation:** Displays the generated SQL query and an explanation from the AI model.
*   **Processing Steps:** Shows the intermediate steps taken by the backend to generate the query.
*   **Schema Viewer:** Allows users to browse the database schema within the application.

## Tech Stack

*   **Backend:** Python, Flask
*   **AI Model:** Azure AI Inference Service (configured via [`config/config.py`](config/config.py) and used in [`src/utils/azure_client.py`](src/utils/azure_client.py))
*   **Database:** SQLite (default), SQLAlchemy
*   **Frontend:** HTML, CSS, JavaScript, Bootstrap 5, jQuery, DataTables
*   **Environment Management:** `python-dotenv`

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
    ```
4.  **Configure Environment Variables:**
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
    *   Refer to [`config/config.py`](config/config.py) for all possible environment variables.
    *   Ensure the `GITHUB_TOKEN` has appropriate permissions if using it for Azure AI authentication.

5.  **Initialize the Database:**
    Run the initialization script to create the SQLite database (`text2sql.db`) and populate it with sample data:
    ```bash
    python src/utils/init_db.py
    ```

## Running the Application

1.  **Start the Flask development server:**
    ```bash
    python app.py
    ```
    Or use the provided restart script (ensure it has execute permissions: `chmod +x restart.sh`):
    ```bash
    ./restart.sh
    ```
2.  Open your web browser and navigate to `http://127.0.0.1:5000` (or the address provided by Flask).

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
├── src/                # Source code
│   ├── agents/         # (Potentially) Agent-based logic components
│   ├── models/         # SQL generation logic
│   └── utils/          # Utility scripts (DB connection, schema manager, AI client)
├── static/             # Frontend assets
│   ├── css/            # Custom stylesheets
│   └── js/             # Custom JavaScript
└── templates/          # HTML templates for Flask
    ├── index.html      # Main application page
    ├── 404.html        # Custom 404 error page
    └── 500.html        # Custom 500 error page
```

## Configuration

*   **Application Settings:** Managed in [`config/config.py`](config/config.py), primarily loaded from environment variables defined in the `.env` file.
*   **Database Schema:** The structure of the database tables, columns, and descriptions used by the AI model is defined in [`config/data/schema.json`](config/data/schema.json). This file needs to be kept in sync with the actual database schema. The [`src/utils/csv_to_schema.py`](src/utils/csv_to_schema.py) script can help generate this from a CSV file, but manual refinement is often necessary.
*   **Logging:** Configured within [`config/config.py`](config/config.py), logs are written to the `logs/` directory.