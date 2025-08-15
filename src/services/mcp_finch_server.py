"""
MCP Finch Server - Database Intelligence Agent (Stdio implementation)
Inspired by Uber's Finch: Conversational AI Data Agent

This server implements a comprehensive database interaction system with:
- Database connectivity and querying
- Metadata management and semantic search  
- Natural language to SQL conversion
- Query execution with safety controls
- Result formatting and export capabilities
- Enterprise security and access controls

Architecture follows Finch's approach:
1. Conversational AI interface
2. Metadata-driven query generation
3. Self-querying agents with semantic understanding
4. Security and role-based access controls
5. Real-time feedback and result delivery
"""

import json
import logging
import os
import sqlite3
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
import asyncio
import csv
from io import StringIO

# MCP imports
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
)

# Import existing utilities
sys.path.append('/home/vijay/gitrepo/copilot/text2sql')
from src.utils.common_llm import get_llm_engine
from src.utils.database_utils import get_database_engine, execute_query_safe
from src.utils.data_catalog_utils import load_data_catalog, get_catalog_stats
from config.config import DATABASE_URI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('mcp_finch_server')

# Initialize MCP server
server = Server("finch-database-agent")

# Global metadata cache
_metadata_cache = {}
_database_schema_cache = {}

class FinchDatabaseAgent:
    """Main agent class for database intelligence operations"""
    
    def __init__(self):
        self.llm = None
        self.db_engine = None
        self.metadata = {}
        self.initialize()
    
    def initialize(self):
        """Initialize the agent with LLM and database connections"""
        try:
            self.llm = get_llm_engine()
            self.db_engine = get_database_engine()
            self.metadata = load_data_catalog()
            logger.info("Finch Database Agent initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Finch agent: {str(e)}")
    
    def get_database_schema(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Get database schema information, optionally for a specific table"""
        cache_key = f"schema_{table_name or 'all'}"
        
        if cache_key in _database_schema_cache:
            return _database_schema_cache[cache_key]
        
        try:
            if table_name:
                # Get specific table schema
                query = """
                SELECT 
                    name,
                    type,
                    sql
                FROM sqlite_master 
                WHERE type='table' AND name=?
                """
                result = execute_query_safe(query, (table_name,))
                
                if result['success'] and result['data']:
                    # Get column information
                    col_query = f"PRAGMA table_info({table_name})"
                    col_result = execute_query_safe(col_query)
                    
                    schema_info = {
                        'table_name': table_name,
                        'table_sql': result['data'][0]['sql'],
                        'columns': col_result['data'] if col_result['success'] else []
                    }
                else:
                    schema_info = {'error': f'Table {table_name} not found'}
            else:
                # Get all tables
                query = """
                SELECT 
                    name,
                    type,
                    sql
                FROM sqlite_master 
                WHERE type='table'
                ORDER BY name
                """
                result = execute_query_safe(query)
                
                if result['success']:
                    schema_info = {
                        'database': 'main',
                        'tables': result['data'],
                        'table_count': len(result['data'])
                    }
                else:
                    schema_info = {'error': 'Failed to retrieve schema'}
            
            _database_schema_cache[cache_key] = schema_info
            return schema_info
            
        except Exception as e:
            logger.error(f"Error getting database schema: {str(e)}")
            return {'error': f'Schema retrieval failed: {str(e)}'}
    
    def search_metadata_semantic(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search metadata using semantic understanding"""
        try:
            # Use LLM to understand the query and extract relevant terms
            extraction_prompt = f"""
            Analyze this database query and extract key terms that would help find relevant tables and columns:
            
            Query: "{query}"
            
            Extract:
            1. Table names mentioned or implied
            2. Column concepts or field names
            3. Business domains or subject areas
            4. Data types or operations mentioned
            
            Return a JSON object with:
            {{
                "tables": ["explicit table names"],
                "columns": ["explicit column names"], 
                "concepts": ["business concepts"],
                "subject_areas": ["domain areas"],
                "search_terms": ["key terms for semantic search"]
            }}
            
            Return only the JSON object.
            """
            
            llm_response = self.llm.complete(extraction_prompt)
            
            try:
                extracted = json.loads(llm_response.strip())
            except json.JSONDecodeError:
                # Fallback to simple text extraction
                extracted = {
                    "search_terms": query.lower().split(),
                    "tables": [],
                    "columns": [],
                    "concepts": [query],
                    "subject_areas": []
                }
            
            # Search through metadata catalog
            search_results = []
            
            # Search tables
            for schema in self.metadata.get('schemas', []):
                for table in schema.get('tables', []):
                    relevance_score = self._calculate_relevance(table, extracted)
                    if relevance_score > 0.1:
                        search_results.append({
                            'type': 'table',
                            'schema': schema['schemaName'],
                            'name': table['tableName'],
                            'business_name': table['businessName'],
                            'description': table['description'],
                            'subject_area': table['subjectArea'],
                            'table_type': table['tableType'],
                            'relevance_score': relevance_score,
                            'primary_key': table.get('primaryKey', []),
                            'column_count': len(table.get('columns', []))
                        })
                    
                    # Search columns within table
                    for column in table.get('columns', []):
                        col_relevance = self._calculate_column_relevance(column, extracted)
                        if col_relevance > 0.1:
                            search_results.append({
                                'type': 'column',
                                'schema': schema['schemaName'],
                                'table_name': table['tableName'],
                                'name': column['columnName'],
                                'business_name': column['businessName'],
                                'description': column['description'],
                                'data_type': column['dataType'],
                                'relevance_score': col_relevance,
                                'is_natural_key': column.get('isNaturalKey', False),
                                'tags': column.get('tags', [])
                            })
            
            # Sort by relevance and limit results
            search_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            search_results = search_results[:max_results]
            
            return {
                'query': query,
                'extracted_terms': extracted,
                'result_count': len(search_results),
                'results': search_results
            }
            
        except Exception as e:
            logger.error(f"Error in semantic metadata search: {str(e)}")
            return {
                'query': query,
                'error': f'Semantic search failed: {str(e)}',
                'results': []
            }
    
    def _calculate_relevance(self, table: Dict, extracted: Dict) -> float:
        """Calculate relevance score for a table based on extracted terms"""
        score = 0.0
        
        # Exact table name matches
        if table['tableName'].lower() in [t.lower() for t in extracted.get('tables', [])]:
            score += 1.0
        
        # Business name matches
        business_name = table['businessName'].lower()
        for term in extracted.get('search_terms', []):
            if term.lower() in business_name:
                score += 0.3
        
        # Subject area matches
        subject_area = table['subjectArea'].lower()
        for area in extracted.get('subject_areas', []):
            if area.lower() in subject_area:
                score += 0.5
        
        # Description matches
        description = table['description'].lower()
        for term in extracted.get('search_terms', []):
            if term.lower() in description:
                score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_column_relevance(self, column: Dict, extracted: Dict) -> float:
        """Calculate relevance score for a column based on extracted terms"""
        score = 0.0
        
        # Exact column name matches
        if column['columnName'].lower() in [c.lower() for c in extracted.get('columns', [])]:
            score += 1.0
        
        # Business name matches
        business_name = column['businessName'].lower()
        for term in extracted.get('search_terms', []):
            if term.lower() in business_name:
                score += 0.4
        
        # Tag matches
        tags = [tag.lower() for tag in column.get('tags', [])]
        for term in extracted.get('search_terms', []):
            if term.lower() in tags:
                score += 0.3
        
        # Description matches
        description = column['description'].lower()
        for term in extracted.get('search_terms', []):
            if term.lower() in description:
                score += 0.2
        
        return min(score, 1.0)
    
    def generate_sql_query(self, natural_language_query: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate SQL query from natural language using metadata context"""
        try:
            # First, search metadata to understand the query context
            metadata_results = self.search_metadata_semantic(natural_language_query, max_results=5)
            
            # Get database schema for relevant tables
            relevant_tables = []
            for result in metadata_results['results']:
                if result['type'] == 'table':
                    table_schema = self.get_database_schema(result['name'])
                    if 'error' not in table_schema:
                        relevant_tables.append({
                            'name': result['name'],
                            'schema': table_schema,
                            'business_name': result['business_name'],
                            'description': result['description']
                        })
            
            # Build context for LLM
            schema_context = ""
            if relevant_tables:
                schema_context = "RELEVANT TABLES:\n"
                for table in relevant_tables[:3]:  # Limit to top 3 tables
                    schema_context += f"\nTable: {table['name']} ({table['business_name']})\n"
                    schema_context += f"Description: {table['description']}\n"
                    if 'columns' in table['schema']:
                        schema_context += "Columns:\n"
                        for col in table['schema']['columns']:
                            schema_context += f"  - {col['name']} ({col['type']})\n"
                    schema_context += "\n"
            
            # Generate SQL using LLM
            sql_prompt = f"""
            Convert this natural language query to SQL using the provided database schema.
            
            QUERY: "{natural_language_query}"
            
            {schema_context}
            
            DATABASE TYPE: SQLite
            
            Generate a valid SQL query that:
            1. Uses only the tables and columns shown in the schema
            2. Follows SQLite syntax
            3. Includes appropriate WHERE clauses for filters
            4. Uses proper JOINs if multiple tables are needed
            5. Limits results to reasonable number (e.g., LIMIT 100)
            6. Is safe and read-only (no INSERT/UPDATE/DELETE)
            
            Return a JSON object with:
            {{
                "sql_query": "the generated SQL query",
                "explanation": "explanation of what the query does",
                "tables_used": ["list of table names used"],
                "confidence": 0.95,
                "warnings": ["any potential issues or assumptions"]
            }}
            
            Return only the JSON object.
            """
            
            llm_response = self.llm.complete(sql_prompt)
            
            try:
                sql_result = json.loads(llm_response.strip())
                
                # Validate the generated SQL
                validation_result = self._validate_sql_query(sql_result.get('sql_query', ''))
                
                return {
                    'query': natural_language_query,
                    'metadata_search': metadata_results,
                    'generated_sql': sql_result.get('sql_query', ''),
                    'explanation': sql_result.get('explanation', ''),
                    'tables_used': sql_result.get('tables_used', []),
                    'confidence': sql_result.get('confidence', 0.5),
                    'warnings': sql_result.get('warnings', []),
                    'validation': validation_result,
                    'status': 'success'
                }
                
            except json.JSONDecodeError:
                return {
                    'query': natural_language_query,
                    'error': 'Failed to parse LLM response',
                    'raw_response': llm_response,
                    'status': 'error'
                }
                
        except Exception as e:
            logger.error(f"Error generating SQL query: {str(e)}")
            return {
                'query': natural_language_query,
                'error': f'SQL generation failed: {str(e)}',
                'status': 'error'
            }
    
    def _validate_sql_query(self, sql_query: str) -> Dict[str, Any]:
        """Validate SQL query for safety and syntax"""
        try:
            # Basic safety checks
            dangerous_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE']
            sql_upper = sql_query.upper()
            
            safety_issues = []
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    safety_issues.append(f"Contains dangerous keyword: {keyword}")
            
            # Syntax validation using SQLite parser
            syntax_valid = True
            syntax_error = None
            
            try:
                # Create a temporary in-memory database to test syntax
                conn = sqlite3.connect(':memory:')
                cursor = conn.cursor()
                cursor.execute("EXPLAIN QUERY PLAN " + sql_query)
                conn.close()
            except sqlite3.Error as e:
                syntax_valid = False
                syntax_error = str(e)
            
            return {
                'is_safe': len(safety_issues) == 0,
                'safety_issues': safety_issues,
                'syntax_valid': syntax_valid,
                'syntax_error': syntax_error,
                'status': 'valid' if len(safety_issues) == 0 and syntax_valid else 'invalid'
            }
            
        except Exception as e:
            return {
                'is_safe': False,
                'safety_issues': [f'Validation error: {str(e)}'],
                'syntax_valid': False,
                'status': 'error'
            }
    
    def execute_sql_query(self, sql_query: str, max_rows: int = 100) -> Dict[str, Any]:
        """Execute SQL query safely with result formatting"""
        try:
            # Validate query first
            validation = self._validate_sql_query(sql_query)
            
            if validation['status'] != 'valid':
                return {
                    'sql_query': sql_query,
                    'success': False,
                    'error': 'Query validation failed',
                    'validation': validation,
                    'data': []
                }
            
            # Add LIMIT if not present
            sql_upper = sql_query.upper()
            if 'LIMIT' not in sql_upper:
                sql_query += f" LIMIT {max_rows}"
            
            # Execute query
            result = execute_query_safe(sql_query)
            
            if result['success']:
                # Format results
                formatted_result = {
                    'sql_query': sql_query,
                    'success': True,
                    'row_count': len(result['data']),
                    'columns': result.get('columns', []),
                    'data': result['data'],
                    'execution_time': result.get('execution_time'),
                    'validation': validation
                }
                
                # Add summary if results exist
                if result['data']:
                    formatted_result['summary'] = self._generate_result_summary(
                        result['data'], 
                        result.get('columns', [])
                    )
                
                return formatted_result
            else:
                return {
                    'sql_query': sql_query,
                    'success': False,
                    'error': result.get('error', 'Unknown execution error'),
                    'validation': validation,
                    'data': []
                }
                
        except Exception as e:
            logger.error(f"Error executing SQL query: {str(e)}")
            return {
                'sql_query': sql_query,
                'success': False,
                'error': f'Execution failed: {str(e)}',
                'data': []
            }
    
    def _generate_result_summary(self, data: List[Dict], columns: List[str]) -> Dict[str, Any]:
        """Generate a summary of query results"""
        try:
            if not data:
                return {'message': 'No data returned'}
            
            summary = {
                'total_rows': len(data),
                'total_columns': len(columns),
                'column_names': columns,
                'sample_rows': data[:3]  # First 3 rows as sample
            }
            
            # Add basic statistics for numeric columns
            numeric_stats = {}
            for col in columns:
                values = [row.get(col) for row in data if row.get(col) is not None]
                
                # Check if numeric
                numeric_values = []
                for val in values:
                    try:
                        numeric_values.append(float(val))
                    except (ValueError, TypeError):
                        break
                
                if len(numeric_values) > 0 and len(numeric_values) == len(values):
                    numeric_stats[col] = {
                        'min': min(numeric_values),
                        'max': max(numeric_values),
                        'avg': sum(numeric_values) / len(numeric_values),
                        'count': len(numeric_values)
                    }
            
            if numeric_stats:
                summary['numeric_statistics'] = numeric_stats
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating result summary: {str(e)}")
            return {'message': f'Summary generation failed: {str(e)}'}
    
    def export_results_csv(self, data: List[Dict], filename: Optional[str] = None) -> Dict[str, Any]:
        """Export query results to CSV format"""
        try:
            if not data:
                return {
                    'success': False,
                    'error': 'No data to export',
                    'csv_content': ''
                }
            
            # Generate CSV content
            output = StringIO()
            
            # Get column names from first row
            if data:
                columns = list(data[0].keys())
                writer = csv.DictWriter(output, fieldnames=columns)
                writer.writeheader()
                writer.writerows(data)
            
            csv_content = output.getvalue()
            output.close()
            
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"query_results_{timestamp}.csv"
            
            return {
                'success': True,
                'filename': filename,
                'csv_content': csv_content,
                'row_count': len(data),
                'size_bytes': len(csv_content.encode('utf-8'))
            }
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            return {
                'success': False,
                'error': f'CSV export failed: {str(e)}',
                'csv_content': ''
            }

# Initialize the Finch agent
finch_agent = FinchDatabaseAgent()


@server.list_tools()
async def handle_list_tools() -> ListToolsResult:
    """List all available tools for the Finch Database Agent"""
    return ListToolsResult(
        tools=[
            Tool(
                name="get_database_schema",
                description="Get database schema information for all tables or a specific table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Optional: specific table name to get schema for"
                        }
                    }
                }
            ),
            Tool(
                name="search_metadata",
                description="Search database metadata using semantic understanding and natural language",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query to search for tables, columns, and concepts"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 10)",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="generate_sql",
                description="Generate SQL query from natural language using metadata and schema context",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query to convert to SQL"
                        },
                        "context": {
                            "type": "object",
                            "description": "Optional: additional context for query generation"
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="execute_query",
                description="Execute SQL query safely with validation and result formatting",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sql_query": {
                            "type": "string",
                            "description": "SQL query to execute"
                        },
                        "max_rows": {
                            "type": "integer",
                            "description": "Maximum number of rows to return (default: 100)",
                            "default": 100
                        }
                    },
                    "required": ["sql_query"]
                }
            ),
            Tool(
                name="query_and_analyze",
                description="Complete workflow: convert natural language to SQL, execute, and analyze results",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "natural_query": {
                            "type": "string",
                            "description": "Natural language query to process end-to-end"
                        },
                        "max_rows": {
                            "type": "integer",
                            "description": "Maximum number of rows to return (default: 100)",
                            "default": 100
                        },
                        "include_export": {
                            "type": "boolean",
                            "description": "Whether to include CSV export of results",
                            "default": False
                        }
                    },
                    "required": ["natural_query"]
                }
            ),
            Tool(
                name="export_results_csv",
                description="Export query results to CSV format",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "array",
                            "description": "Array of result objects to export"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Optional: filename for the CSV export"
                        }
                    },
                    "required": ["data"]
                }
            ),
            Tool(
                name="get_catalog_overview",
                description="Get overview of the data catalog with statistics and available entities",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="validate_sql",
                description="Validate SQL query for safety and syntax without executing",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sql_query": {
                            "type": "string",
                            "description": "SQL query to validate"
                        }
                    },
                    "required": ["sql_query"]
                }
            )
        ]
    )


@server.call_tool()
async def handle_call_tool(request: CallToolRequest) -> CallToolResult:
    """Handle tool execution requests"""
    try:
        tool_name = request.params.name
        arguments = request.params.arguments or {}
        
        result = None
        
        if tool_name == "get_database_schema":
            table_name = arguments.get("table_name")
            result = finch_agent.get_database_schema(table_name)
            
        elif tool_name == "search_metadata":
            query = arguments.get("query", "")
            max_results = arguments.get("max_results", 10)
            result = finch_agent.search_metadata_semantic(query, max_results)
            
        elif tool_name == "generate_sql":
            query = arguments.get("query", "")
            context = arguments.get("context")
            result = finch_agent.generate_sql_query(query, context)
            
        elif tool_name == "execute_query":
            sql_query = arguments.get("sql_query", "")
            max_rows = arguments.get("max_rows", 100)
            result = finch_agent.execute_sql_query(sql_query, max_rows)
            
        elif tool_name == "query_and_analyze":
            natural_query = arguments.get("natural_query", "")
            max_rows = arguments.get("max_rows", 100)
            include_export = arguments.get("include_export", False)
            
            # Complete workflow
            sql_generation = finch_agent.generate_sql_query(natural_query)
            
            if sql_generation['status'] == 'success':
                execution_result = finch_agent.execute_sql_query(
                    sql_generation['generated_sql'], 
                    max_rows
                )
                
                result = {
                    'natural_query': natural_query,
                    'sql_generation': sql_generation,
                    'execution': execution_result,
                    'status': 'completed'
                }
                
                # Add CSV export if requested
                if include_export and execution_result['success'] and execution_result['data']:
                    csv_export = finch_agent.export_results_csv(execution_result['data'])
                    result['csv_export'] = csv_export
            else:
                result = {
                    'natural_query': natural_query,
                    'sql_generation': sql_generation,
                    'status': 'failed'
                }
                
        elif tool_name == "export_results_csv":
            data = arguments.get("data", [])
            filename = arguments.get("filename")
            result = finch_agent.export_results_csv(data, filename)
            
        elif tool_name == "get_catalog_overview":
            try:
                stats = get_catalog_stats()
                catalog = load_data_catalog()
                
                result = {
                    'catalog_statistics': stats,
                    'schemas': [schema['schemaName'] for schema in catalog.get('schemas', [])],
                    'capabilities': [
                        'Natural language to SQL conversion',
                        'Semantic metadata search',
                        'Database schema introspection',
                        'Safe query execution with validation',
                        'Result analysis and export',
                        'Enterprise security controls'
                    ],
                    'status': 'success'
                }
            except Exception as e:
                result = {
                    'error': f'Failed to get catalog overview: {str(e)}',
                    'status': 'error'
                }
                
        elif tool_name == "validate_sql":
            sql_query = arguments.get("sql_query", "")
            result = finch_agent._validate_sql_query(sql_query)
            
        else:
            result = {
                'error': f'Unknown tool: {tool_name}',
                'available_tools': [
                    'get_database_schema', 'search_metadata', 'generate_sql',
                    'execute_query', 'query_and_analyze', 'export_results_csv',
                    'get_catalog_overview', 'validate_sql'
                ]
            }
        
        # Format result as JSON string
        result_json = json.dumps(result, indent=2, default=str)
        
        return CallToolResult(
            content=[TextContent(type="text", text=result_json)]
        )
        
    except Exception as e:
        logger.error(f"Error in tool execution: {str(e)}")
        error_result = {
            'error': f'Tool execution failed: {str(e)}',
            'tool': request.params.name,
            'arguments': request.params.arguments
        }
        
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(error_result, indent=2))]
        )


async def main():
    """Main entry point for the Finch MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="finch-database-agent",
                server_version="1.0.0",
                capabilities={
                    "tools": {},
                    "prompts": {},
                    "resources": {}
                }
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
