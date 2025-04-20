# Text2SQL Assistant

A web application that translates natural language questions into SQL queries, executes them against a database, and displays the results. It uses AI (Azure AI Inference) and incorporates feedback mechanisms to improve accuracy over time.

## Key Features

*   **Natural Language to SQL:** Converts English questions to SQL.
*   **Database Interaction:** Executes SQL and shows results.
*   **Schema Awareness:** Uses database schema details for better query generation.
*   **Knowledge Base Q&A:** Answers questions based on uploaded documents using vector search.
*   **User Feedback:** Collects feedback to refine query generation.
*   **Sample Management:** Uses curated and successful past queries as examples for the AI.
*   **User Management & RBAC:** Secure login, user roles, and permissions.
*   **Admin Dashboard:** Tools for user/role management, audit logs, and system monitoring.
*   **Admin DB Query Editor:** Interface for admins to execute raw SQL queries.
*   **Configuration Management UI:** Allows admins to manage application settings via the UI.
*   **Metadata Search:** Functionality to search database metadata.
*   **SQL Query Editor:** A dedicated interface for writing/editing SQL queries.
*   **Vector DB Management UI:** Interface for admins to manage the vector database.
*   **Security:** Includes features like CSRF protection, secure headers, and rate limiting.

## Tech Stack

*   **Backend:** Python, Flask, SQLAlchemy
*   **AI:** Azure AI Inference Service, Sentence-Transformers
*   **Frontend:** HTML, CSS, JavaScript, Bootstrap 5, jQuery
*   **Database:** SQLite (default)

## Setup and Installation

1.  **Clone:** `git clone <repository-url> && cd text2sql`
2.  **Environment:** `python -m venv venv && source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
3.  **Install:** `pip install -r requirements.txt`
4.  **Configure:** Create a `.env` file (copy `.env.example` if available) and fill in `AZURE_ENDPOINT`, `AZURE_MODEL_NAME`, `GITHUB_TOKEN` (for Azure auth), `DATABASE_URI`, and `SECRET_KEY`. See `config/config.py` for more options.
5.  **Initialize DB:** `python src/utils/init_db.py` (Creates DB and default admin user: admin/admin123 - **change immediately!**)

## Running the Application

1.  **Start Server:** `python app.py` or `./restart.sh`
2.  **Access:** Open `http://127.0.0.1:5000` in your browser.
3.  **Login:** Use the default admin credentials and change the password via the admin panel.

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
├── logs/               # Log files
├── uploads/            # Uploaded knowledge base documents
└── text2sql.db         # Default SQLite database
```

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