from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from src.utils.schema_manager import SchemaManager
import pandas as pd
import logging
import time
from config.config import DATABASE_URI

class DatabaseManager:
    def __init__(self, connection_string=None):
        """Initialize the database manager with a connection string
        
        Args:
            connection_string (str, optional): SQLAlchemy connection string, defaults to config
        """
        self.logger = logging.getLogger('text2sql.database')
        self.connection_string = connection_string or DATABASE_URI
        self.logger.info(f"Database manager initialized with connection: {self.connection_string}")
        self.engine = None
        
    def connect(self):
        """Establish database connection"""
        start_time = time.time()
        self.logger.info("Attempting database connection")
        
        try:
            self.engine = create_engine(self.connection_string)
            self.logger.info(f"Database connection established in {time.time() - start_time:.2f}s")
            return True
        except Exception as e:
            self.logger.error(f"Database connection error: {str(e)}", exc_info=True)
            print(f"Database connection error: {e}")
            return False
    
    def execute_query(self, sql_query):
        """Execute an SQL query and return results
        
        Args:
            sql_query (str): The SQL query to execute
            
        Returns:
            dict: Dictionary with query results and metadata
        """
        start_time = time.time()
        self.logger.info(f"Executing SQL query: {sql_query}")
        
        if not self.engine:
            self.logger.warning("No active database connection, attempting to connect")
            if not self.connect():
                self.logger.error("Failed to connect to database to execute query")
                return {"error": "Database connection failed", "data": None}
        
        try:
            # Execute the query and fetch results
            with self.engine.connect() as conn:
                self.logger.debug("Query execution started")
                execution_start = time.time()
                result = conn.execute(text(sql_query))
                data = result.fetchall()
                execution_time = time.time() - execution_start
                self.logger.debug(f"Query execution completed in {execution_time:.2f}s")
                
                # Convert to pandas DataFrame for easier data manipulation
                if data:
                    df = pd.DataFrame(data, columns=result.keys())
                    self.logger.info(f"Query returned {len(df)} rows with {len(df.columns)} columns")
                    
                    # Log sample data (first few rows) at debug level
                    if len(df) > 0:
                        sample_size = min(3, len(df))
                        sample_df = df.head(sample_size)
                        self.logger.debug(f"Sample data (first {sample_size} rows):\n{sample_df.to_string()}")
                    
                    processing_time = time.time() - start_time
                    self.logger.info(f"Query processing completed in {processing_time:.2f}s")
                    
                    return {
                        "success": True,
                        "data": df,
                        "row_count": len(df),
                        "columns": df.columns.tolist(),
                        "error": None,
                        "execution_time": execution_time
                    }
                else:
                    self.logger.info("Query executed successfully but returned no rows")
                    processing_time = time.time() - start_time
                    self.logger.info(f"Query processing completed in {processing_time:.2f}s")
                    
                    return {
                        "success": True,
                        "data": None,
                        "row_count": 0,
                        "columns": result.keys(),
                        "error": None,
                        "execution_time": execution_time
                    }
                    
        except SQLAlchemyError as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            self.logger.error(f"SQL error after {processing_time:.2f}s: {error_msg}", exc_info=True)
            
            return {
                "success": False,
                "data": None,
                "row_count": 0,
                "columns": [],
                "error": error_msg,
                "execution_time": processing_time
            }
    
    def get_query_examples(self, table_name=None, limit=5):
        """Get example queries for a given table or the database
        
        Args:
            table_name (str, optional): Specific table to get examples for
            limit (int, optional): Maximum number of examples to return
            
        Returns:
            list: Example queries with matching SQL
        """
        self.logger.debug(f"Getting query examples for table: {table_name if table_name else 'all tables'}")
        examples = []
        
        # Use schema manager to get table information
        schema_manager = SchemaManager()
        
        # Add table-specific examples if table_name is provided
        if table_name:
            self.logger.debug(f"Generating examples for table: {table_name}")
            examples.extend(self._generate_table_examples(table_name, schema_manager))
        else:
            # General database examples based on schema
            self.logger.debug("Generating general database examples")
            examples = [
                {
                    "question": "How many tables are in the database?",
                    "sql": "SELECT COUNT(*) AS table_count FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                }
            ]
            
            # Add example using first table found
            tables = schema_manager.get_table_names()
            if tables:
                first_table = tables[0]
                examples.extend([
                    {
                        "question": f"Show me the first 10 rows of the {first_table} table",
                        "sql": f"SELECT * FROM {first_table} LIMIT 10"
                    },
                    {
                        "question": f"Get the total number of records in the {first_table} table",
                        "sql": f"SELECT COUNT(*) AS total_records FROM {first_table}"
                    }
                ])
        
        self.logger.debug(f"Generated {len(examples)} example queries (limit: {limit})")
        return examples[:limit]
    
    def _generate_table_examples(self, table_name, schema_manager):
        """Generate example queries for a specific table using schema information
        
        Args:
            table_name (str): Name of the table
            schema_manager (SchemaManager): Instance of schema manager
            
        Returns:
            list: Example queries with matching SQL
        """
        self.logger.debug(f"Generating example queries for table: {table_name}")
        examples = [
            {
                "question": f"How many records are in the {table_name} table?",
                "sql": f"SELECT COUNT(*) AS record_count FROM {table_name}"
            },
            {
                "question": f"Show me the first 10 rows of the {table_name} table",
                "sql": f"SELECT * FROM {table_name} LIMIT 10"
            }
        ]
        
        # Get table information from schema
        table = schema_manager.get_table_by_name(table_name)
        if table:
            columns = table["columns"]
            
            if columns:
                # Find a good text column for DISTINCT example (prefer name, description, or type columns)
                text_cols = [col for col in columns if col["datatype"].upper() == "TEXT"]
                name_cols = [col for col in text_cols if any(x in col["name"].lower() for x in ["name", "type", "category", "status"])]
                
                if name_cols:
                    col = name_cols[0]
                    examples.append({
                        "question": f"What are the distinct values of {col['name']} in the {table_name} table?",
                        "sql": f"SELECT DISTINCT {col['name']} FROM {table_name}"
                    })
                
                # Find numeric columns for aggregation examples
                numeric_cols = [col for col in columns if col["datatype"].upper() in ("INTEGER", "REAL", "DECIMAL", "NUMBER")]
                
                # If we have both categorical and numeric columns, create aggregate example
                if text_cols and numeric_cols:
                    group_col = name_cols[0] if name_cols else text_cols[0]
                    agg_col = numeric_cols[0]
                    
                    examples.append({
                        "question": f"Get total {agg_col['name']} grouped by {group_col['name']} in the {table_name} table",
                        "sql": f"SELECT {group_col['name']}, SUM({agg_col['name']}) as total_{agg_col['name']} "
                              f"FROM {table_name} "
                              f"GROUP BY {group_col['name']}"
                    })
                
                # Add example with primary key lookup if available
                primary_keys = [col for col in columns if col.get("is_primary_key")]
                if primary_keys:
                    pk = primary_keys[0]
                    examples.append({
                        "question": f"Get record from {table_name} where {pk['name']} is 1",
                        "sql": f"SELECT * FROM {table_name} WHERE {pk['name']} = 1"
                    })
                
                # If this is orders or similar transactional table, add date-based example
                date_cols = [col for col in columns if "date" in col["name"].lower()]
                if date_cols:
                    date_col = date_cols[0]
                    examples.append({
                        "question": f"Get {table_name} from the last 30 days",
                        "sql": f"SELECT * FROM {table_name} "
                              f"WHERE {date_col['name']} >= date('now', '-30 days')"
                    })
                    
        return examples
    
    def close(self):
        """Close database connections"""
        self.logger.info("Closing database connection")
        if self.engine:
            self.engine.dispose()
            self.logger.debug("Database engine disposed")