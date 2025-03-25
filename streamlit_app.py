import streamlit as st
import pandas as pd
import time
import os
import logging
import sys
import uuid
import json
import plotly.express as px
from datetime import datetime

from src.models.sql_generator import SQLGenerationManager
from src.utils.schema_manager import SchemaManager
from config.config import DEBUG, GITHUB_TOKEN

# Configure logging
def setup_logging(log_level=logging.DEBUG):
    """Configure application logging"""
    # Get the logger but first remove any existing handlers
    app_logger = logging.getLogger('text2sql')
    
    # Remove any existing handlers to prevent duplicates
    if app_logger.hasHandlers():
        app_logger.handlers.clear()
    
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    app_logger.setLevel(log_level)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler - only add if none exists
    if not any(isinstance(h, logging.StreamHandler) for h in app_logger.handlers):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        app_logger.addHandler(console_handler)
    
    # File handlers - only add if they don't exist
    handlers = {
        'text2sql.log': logging.DEBUG,
        'error.log': logging.ERROR,
        'queries.log': logging.INFO
    }
    
    existing_files = {h.baseFilename for h in app_logger.handlers if isinstance(h, logging.FileHandler)}
    
    for filename, level in handlers.items():
        filepath = os.path.join(log_dir, filename)
        if filepath not in existing_files:
            handler = logging.FileHandler(filepath)
            handler.setLevel(level)
            handler.setFormatter(formatter)
            app_logger.addHandler(handler)
    
    return app_logger

# Initialize logger
logger = setup_logging(logging.DEBUG if DEBUG else logging.INFO)

# Define workspaces
workspaces = [
    {
        "name": "Default",
        "description": "Default workspace with access to all tables"
    },
    {
        "name": "Sales",
        "description": "Sales-related data including customers, orders, and products"
    },
    {
        "name": "Analytics",
        "description": "Analytical data for business intelligence and reporting"
    }
]

# Initialize the SQL generation manager
@st.cache_resource
def get_sql_manager():
    return SQLGenerationManager()

def get_schema_data(workspace_name="Default"):
    """Get schema data from the schema manager"""
    start_time = time.time()
    logger.info(f"Schema requested for workspace: {workspace_name}")
    
    try:
        sql_manager = get_sql_manager()
        
        # Get schema data
        tables = sql_manager.schema_manager.get_tables(workspace_name)
        
        # Convert tables to a simpler format for frontend
        schema_data = []
        for table in tables:
            table_info = {
                "name": table["name"],
                "description": table.get("description", ""),
                "columns": []
            }
            
            for col in table.get("columns", []):
                column_info = {
                    "name": col["name"],
                    "datatype": col["datatype"],
                    "description": col.get("description", ""),
                    "is_primary_key": col.get("is_primary_key", False)
                }
                table_info["columns"].append(column_info)
            
            schema_data.append(table_info)
        
        processing_time = time.time() - start_time
        logger.debug(f"Schema retrieval completed in {processing_time:.3f}s")
        
        return schema_data
        
    except Exception as e:
        logger.exception(f"Error retrieving database schema: {str(e)}")
        return []

def process_query(query, workspace_name="Default"):
    """Process a natural language query and return results"""
    
    if not query:
        return {
            "success": False,
            "error": "No query provided"
        }
    
    logger.info(f"Processing query: '{query}'")
    
    # Create a placeholder for storing processing steps
    progress_steps = []
    
    # Create a placeholder for displaying live updates
    status_placeholder = st.empty()
    current_step = 0
    
    def progress_callback(step):
        nonlocal current_step
        progress_steps.append(step)
        current_step += 1
        
        # Update the status display with the current step
        with status_placeholder.container():
            st.write(f"Step {current_step}: {step.get('description', 'Processing')}")
            
            # Display step result if available
            result_content = step.get("result")
            if isinstance(result_content, str):
                if result_content.strip().startswith("SELECT") or "SELECT" in result_content[:20]:
                    st.code(result_content, language="sql")
                else:
                    st.write(result_content)
            elif result_content:
                st.json(result_content)
    
    try:
        sql_manager = get_sql_manager()
        selected_workspaces = [w for w in workspaces if w['name'] == workspace_name]
        
        # Process query using SQL generation manager
        result = sql_manager.process_query(query, selected_workspaces, progress_callback=progress_callback)
        
        # Add progress steps to result
        result["steps"] = progress_steps
        result["success"] = True
        return result
        
    except Exception as e:
        logger.exception(f"Exception while processing query: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "steps": progress_steps
        }

def display_schema_table(schema_data):
    """Display the database schema in a formatted table"""
    
    # Create tabs for each table
    tabs = st.tabs([table["name"] for table in schema_data])
    
    for i, tab in enumerate(tabs):
        table = schema_data[i]
        
        with tab:
            st.write(f"**{table['name']}**")
            st.write(table.get("description", ""))
            
            # Convert columns to DataFrame for display
            columns_data = []
            for col in table.get("columns", []):
                columns_data.append({
                    "Column": col["name"],
                    "Type": col["datatype"],
                    "Primary Key": "✓" if col.get("is_primary_key", False) else "",
                    "Description": col.get("description", "")
                })
            
            if columns_data:
                df = pd.DataFrame(columns_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.write("No columns available")

def format_sql(sql):
    """Format SQL with syntax highlighting"""
    return f"""```sql
{sql}
```"""

def display_chart(chart_data):
    """Display a chart based on query results"""
    if not chart_data or not chart_data.get("data"):
        return
    
    data = chart_data.get("data", [])
    columns = chart_data.get("columns", [])
    
    if not data or not columns:
        return
    
    df = pd.DataFrame(data)
    
    # Check if we have numeric columns that can be used for charts
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    
    if not numeric_cols:
        return
    
    # Create chart options
    chart_type = st.selectbox(
        "Select chart type:",
        ["Bar Chart", "Line Chart", "Scatter Plot", "Pie Chart"],
        key="chart_type"
    )
    
    if chart_type == "Bar Chart" and categorical_cols:
        x_axis = st.selectbox("Select X-axis (categorical):", categorical_cols, key="bar_x")
        y_axis = st.selectbox("Select Y-axis (numeric):", numeric_cols, key="bar_y")
        chart = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} by {x_axis}")
        st.plotly_chart(chart, use_container_width=True)
        
    elif chart_type == "Line Chart" and len(df) > 1:
        if categorical_cols:
            x_axis = st.selectbox("Select X-axis:", categorical_cols, key="line_x")
            y_axis = st.selectbox("Select Y-axis:", numeric_cols, key="line_y")
            chart = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} over {x_axis}")
            st.plotly_chart(chart, use_container_width=True)
        else:
            y_axis = st.selectbox("Select Y-axis:", numeric_cols, key="line_y")
            chart = px.line(df, y=y_axis, title=f"{y_axis} values")
            st.plotly_chart(chart, use_container_width=True)
            
    elif chart_type == "Scatter Plot" and len(numeric_cols) >= 2:
        x_axis = st.selectbox("Select X-axis:", numeric_cols, key="scatter_x")
        y_axis = st.selectbox("Select Y-axis:", [col for col in numeric_cols if col != x_axis], key="scatter_y")
        chart = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")
        st.plotly_chart(chart, use_container_width=True)
        
    elif chart_type == "Pie Chart" and categorical_cols and numeric_cols:
        names = st.selectbox("Select names (categorical):", categorical_cols, key="pie_names")
        values = st.selectbox("Select values (numeric):", numeric_cols, key="pie_values")
        chart = px.pie(df, names=names, values=values, title=f"{values} by {names}")
        st.plotly_chart(chart, use_container_width=True)

def main():
    # Set page configuration
    st.set_page_config(
        page_title="Text2SQL Assistant",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Update the custom CSS to set both margin and padding of the block-container to 20px
    st.markdown(
        """
        <style>
        .block-container {
            margin-left: 20px !important;
            margin-right: 20px !important;
            padding-left: 20px !important;
            padding-right: 20px !important;
            padding-top: 20px !important;
            padding-bottom: 20px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Check for GitHub token
    if not GITHUB_TOKEN:
        st.error("Error: GITHUB_TOKEN environment variable is not set.")
        st.error("Please set your GitHub token as an environment variable: export GITHUB_TOKEN=your_token_here")
        return
    
    # Title and description
    st.title("Text2SQL Assistant")
    st.markdown("""
    Convert natural language questions into SQL queries. Ask questions about your data and get instant SQL!
    """)
    
    # Sidebar for workspace selection
    with st.sidebar:
        st.header("Workspace")
        workspace_options = [w["name"] for w in workspaces]
        workspace_descriptions = {w["name"]: w["description"] for w in workspaces}
        
        selected_workspace = st.selectbox(
            "Select a workspace:",
            workspace_options,
            index=0,
            key="workspace_select"
        )
        
        # Show workspace description
        st.caption(workspace_descriptions.get(selected_workspace, ""))
        
        # View schema button
        if st.button("View Database Schema"):
            st.session_state.show_schema = True
        else:
            if "show_schema" not in st.session_state:
                st.session_state.show_schema = False
        
        # Example queries section
        st.subheader("Example Queries")
        example_queries = [
            "How many customers do we have?",
            "Show me all products with price greater than $200",
            "What was our revenue in January?",
            "Which customers made the most orders?",
            "Show the sales by month"
        ]
        
        for query in example_queries:
            if st.button(query, key=f"example_{hash(query)}"):
                st.session_state.query = query
                st.session_state.run_query = True

    # Initialize session state variables if they don't exist
    if "query" not in st.session_state:
        st.session_state.query = ""
    if "run_query" not in st.session_state:
        st.session_state.run_query = False
    
    # Define callback to update query and trigger processing
    def handle_form_submit():
        if "query_input" in st.session_state:
            # Explicitly update the session state query with the current input value
            st.session_state.query = st.session_state.query_input
            # Set the flag to run the query
            st.session_state.run_query = True
    
    # Query input section
    st.write("### Ask a question about your data")
    
    # Create a container for the input and button to be side by side
    input_container = st.container()
    
    # Place input and button side by side
    left_col, right_col = input_container.columns([5, 1])
    
    # Text input field - directly bind to a temporary state variable
    with left_col:
        # Initialize the input field with the current query value
        if "query_input" not in st.session_state:
            st.session_state.query_input = st.session_state.query
            
        st.text_area(
            "",  # No label, we have the header above
            key="query_input",  # Use a different key than the session state variable
            placeholder="Example: How many customers made purchases last month?",
            label_visibility="collapsed"  # Hide the label
        )
    
    # Submit button
    with right_col:
        if st.button("Submit", on_click=handle_form_submit, help="Submit your query"):
            # This code won't run due to the on_click callback
            pass
    
    # Automatically close the schema after displaying it
    if st.session_state.get("show_schema", False):
        st.subheader("Database Schema")

        with st.spinner("Loading schema..."):
            schema_data = get_schema_data(selected_workspace)

        if schema_data:
            display_schema_table(schema_data)
        else:
            st.error("Error loading schema. Please check logs for details.")

        # Automatically reset the show_schema flag to close the schema
        st.session_state.show_schema = False

        st.divider()
    
    # Process query if run_query is True
    if st.session_state.get("run_query", False) and st.session_state.get("query"):
        query = st.session_state.query
        
        # Create a processing status indicator that will be updated in real-time
        with st.status("Processing your query...", expanded=True) as status:
            # Process the query - the progress_callback will update the UI in real-time
            result = process_query(query, selected_workspace)
            
            if result.get("success", False):
                status.update(label="Query processed successfully!", state="complete")
            else:
                st.error(f"Error: {result.get('error', 'An unknown error occurred')}")
                status.update(label="Query processing failed", state="error")
        
        # Display results if available
        if result.get("success", False):
            st.subheader("Results")
            
            # Create tabs for results, SQL, explanation, and steps
            tabs = st.tabs(["Data", "SQL Query", "Explanation", "Processing Steps"])
            
            with tabs[0]:  # Data tab
                if result.get("chart_data") and result["chart_data"].get("data"):
                    # Show number of results
                    st.info(f"Found {result['chart_data']['row_count']} results")
                    
                    # Convert to DataFrame and display without index
                    data_df = pd.DataFrame(result["chart_data"]["data"])
                    st.dataframe(data_df, use_container_width=True, hide_index=True)  # Hide index column
                    
                    # Display charts for numeric data
                    if not data_df.empty and len(result["chart_data"]["data"]) > 1:
                        st.subheader("Visualize Results")
                        display_chart(result["chart_data"])
                else:
                    if result.get("error"):
                        st.error(f"SQL Error: {result['error']}")
                    elif result.get("explanation"):
                        st.info(result["explanation"])
                    else:
                        st.info("No data returned from query")
            
            with tabs[1]:  # SQL Query tab
                if result.get("sql"):
                    st.code(result["sql"], language="sql")
                    # Add copy button
                    st.button("Copy SQL to Clipboard", 
                             on_click=lambda: st.write("SQL copied to clipboard!"))
                else:
                    st.info("No SQL query was generated")
            
            with tabs[2]:  # Explanation tab
                if result.get("explanation"):
                    st.write(result["explanation"])
                else:
                    st.info("No explanation available")
            
            with tabs[3]:  # Processing Steps tab
                steps = result.get("steps", [])
                if steps:
                    for i, step in enumerate(steps):
                        with st.expander(f"Step {i+1}: {step.get('description', 'Processing step')}"):
                            st.write(f"**{step.get('step', 'Step')}**")
                            
                            # Display step result
                            result_content = step.get("result")
                            if isinstance(result_content, str):
                                if result_content.strip().startswith("SELECT") or "SELECT" in result_content[:20]:
                                    st.code(result_content, language="sql")
                                else:
                                    st.write(result_content)
                            elif result_content:
                                st.json(result_content)
                else:
                    st.info("No processing steps available")
        
        # Reset run_query flag
        st.session_state.run_query = False

if __name__ == "__main__":
    main()