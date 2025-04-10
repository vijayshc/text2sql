from azure.ai.inference.models import SystemMessage, UserMessage
import logging
import time
import json
from src.utils.llm_engine import LLMEngine

class AzureAIClient:
    def __init__(self):
        """Initialize the Azure AI Client using the LLM Engine"""
        self.logger = logging.getLogger('text2sql.azure')
        self.logger.info("Initializing Azure AI Client using LLM Engine")
        
        try:
            # Create LLM Engine instance for centralized LLM interaction
            self.llm_engine = LLMEngine()
            self.model_name = self.llm_engine.model_name
            self.logger.info("Azure AI Client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Azure AI Client: {str(e)}", exc_info=True)
            raise
    
    def generate_sql(self, query, schema=None, examples=None, join_conditions=None):
        """Generate SQL from a natural language query
        
        Args:
            query (str): The natural language query
            schema (str, optional): The database schema information
            examples (list, optional): Example queries and corresponding SQL
            join_conditions (list, optional): Pre-defined join conditions between tables
            
        Returns:
            dict: A dictionary containing the generated SQL and explanation
        """
        start_time = time.time()
        self.logger.info(f"SQL generation started for query: '{query}'")
        
        messages = [
            SystemMessage("""You are an expert SQL assistant. Convert natural language questions into precise, executable SQL queries.
Your task is to:
1. Analyze the provided schema carefully, noting table relationships and column types
2. Generate a SQL query that accurately answers the user's question
3. Consider performance by selecting only necessary columns
4. Use appropriate JOIN conditions based on primary/foreign key relationships or provided join conditions
5. Include a brief explanation of your query

Rules:
- Include table names and column references exactly as provided in the schema
- Use appropriate SQL functions based on column data types
- Consider NULL values in your conditions
- Use table aliases for better readability when joining multiple tables
- Add column aliases for computed values
- Format the SQL query with proper indentation
- If similar queries are provided, strictly use that as format or syntax
- Return the SQL inside a code block tagged with ```sql

Example output format:
Here's a query that will [explanation]...

```sql
SELECT ...
FROM ...
WHERE ...
```""")
        ]
        
        # Add schema information if provided
        if schema:
            schema_length = len(schema)
            self.logger.info(f"Including schema information ({schema_length} chars)")
            messages.append(UserMessage(f"Here's the database schema:\n{schema}"))
        else:
            self.logger.info("No schema information provided")
        
        # Add join conditions if provided
        if join_conditions and len(join_conditions) > 0:
            self.logger.info(f"Including {len(join_conditions)} join conditions")
            join_text = "Use the following pre-defined join conditions when joining these tables:\n"
            
            for join in join_conditions:
                left_table = join.get("left_table", "")
                right_table = join.get("right_table", "")
                join_type = join.get("join_type", "INNER")
                condition = join.get("condition", "")
                
                join_text += f"- When joining {left_table} with {right_table}, use: {join_type} JOIN {right_table} ON {condition}\n"
                
            messages.append(UserMessage(join_text))
        
        # Add examples if provided
        if examples and len(examples) > 0:
            # Check if any examples are from similarity search (tagged with source)
            similarity_examples = [ex for ex in examples if ex.get('source') in ['feedback', 'manual']]
            
            # If we have similarity search examples, only use those
            if similarity_examples:
                source_type = similarity_examples[0].get('source', 'similarity')
                self.logger.info(f"Including {len(similarity_examples)} SQL examples from {source_type} similarity search")
                example_text = f"Here are some similar queries that were previously successful:\n"
                for example in similarity_examples:
                    example_text += f"Question: {example['question']}\nSQL: {example['sql']}\n\n"
                messages.append(UserMessage(example_text))
            # Only if no similarity examples were found, fall back to provided examples
            else:
                self.logger.info(f"Including {len(examples)} SQL examples (no similarity examples found)")
                example_text = "Here are some example queries and their SQL:\n"
                for example in examples:
                    example_text += f"Question: {example['question']}\nSQL: {example['sql']}\n\n"
                messages.append(UserMessage(example_text))
        else:
            self.logger.info("No SQL examples provided")
        
        # Add the user query
        messages.append(UserMessage(f"Convert this question to SQL: {query}"))
        self.logger.info(f"PROMPT: {messages}")
        try:
            # Use the LLM Engine instead of directly calling the API
            raw_response = self.llm_engine.generate_completion(messages, log_prefix="SQL_GEN")
            
            result = self._parse_sql_from_response(raw_response)
            
            # Log the extracted SQL
            sql_query = result.get("sql", "")
            if sql_query:
                self.logger.info(f"Generated SQL: {sql_query}")
                # Log to the dedicated query logger as well
                query_logger = logging.getLogger('text2sql.queries')
                query_logger.info(f"QUERY: '{query}' → SQL: {sql_query}")
            else:
                self.logger.warning("No SQL was extracted from the model response")
            
            processing_time = time.time() - start_time
            self.logger.info(f"SQL generation completed in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"SQL generation error after {processing_time:.2f}s: {str(e)}", exc_info=True)
            return {"error": str(e), "sql": "", "explanation": ""}
    
    def _parse_sql_from_response(self, content):
        """Extract SQL query and explanation from model response
        
        Args:
            content (str): The model response content
            
        Returns:
            dict: Dictionary with extracted SQL and explanation
        """
        self.logger.info("Parsing SQL from model response")
        # Simple extraction for SQL code blocks
        sql = ""
        explanation = ""
        
        # Check if content contains a SQL code block
        if "```sql" in content:
            self.logger.info("Found SQL code block in response")
            parts = content.split("```sql")
            if len(parts) > 1:
                sql_block = parts[1].split("```")[0].strip()
                sql = sql_block
                
                # Get explanation (text before or after SQL block)
                pre_explanation = parts[0].strip()
                post_parts = content.split("```")
                post_explanation = post_parts[-1].strip() if len(post_parts) > 2 else ""
                
                explanation = pre_explanation + " " + post_explanation
                explanation = explanation.strip()
                
                self.logger.info(f"Extracted SQL query ({len(sql)} chars) and explanation ({len(explanation)} chars)")
        else:
            # Fallback if no code block formatting
            self.logger.info("No SQL code block found, using entire response as SQL")
            sql = content
            explanation = "No specific explanation provided by the model."
        
        return {
            "sql": sql,
            "explanation": explanation,
            "raw_response": content
        }
    
    def analyze_for_dashboard(self, query, sql, columns, data_sample):
        """Analyze SQL query results to determine if it's suitable for dashboard visualization
        
        Args:
            query (str): The original natural language query
            sql (str): The SQL query that was executed
            columns (list): List of column names in the result
            data_sample (list): Sample of data rows for analysis (typically first 5 rows)
            
        Returns:
            dict: Dashboard recommendations including visualization type, axes, and titles
        """
        start_time = time.time()
        self.logger.info(f"Dashboard analysis started for query: '{query}'")
        
        # Convert data sample to a readable format
        sample_str = ""
        for row_idx, row in enumerate(data_sample[:5]):  # Limiting to first 5 rows max
            sample_str += f"Row {row_idx+1}: {json.dumps(row)}\n"
            
        # Construct a message for the AI to analyze the results
        messages = [
            SystemMessage("""You are a data visualization expert. Analyze the given query results and determine if they're suitable for a dashboard visualization.

Your task is to:
1. Analyze the columns and data
2. Determine if the data is suitable for visualization (has numeric values and categorical data)
3. If suitable, recommend the best chart type (bar, line, pie, etc.)
4. Identify the best columns for X and Y axes (or equivalent based on chart type). Only one column for each axis
5. Suggest meaningful labels and title

Return your analysis in JSON format exactly like this:
{
  "is_suitable": true_or_false,
  "reason": "brief explanation of why it is or isn't suitable",
  "chart_type": "recommended chart type if suitable",
  "x_axis": {
    "column": "column_name for x-axis",
    "label": "suggested x-axis label"
  },
  "y_axis": {
    "column": "column_name for y-axis",
    "label": "suggested y-axis label"
  },
  "title": "suggested chart title"
}

Make decisions based on these criteria:
- Bar charts are good for comparing categories
- Line charts are good for time series 
- Pie charts are good for part-to-whole relationships (under 7 categories)
- Scatter plots are good for showing relationships between numeric values
- Data needs at least one numeric column for most visualizations"""),
            
            UserMessage(f"""Query: {query}
SQL: {sql}
Columns: {', '.join(columns)}
Data Sample:
{sample_str}

Analyze if this data is suitable for a dashboard visualization. If so, provide recommendations in the required JSON format.""")
        ]
        
        try:
            # Use LLM to analyze the query results
            raw_response = self.llm_engine.generate_completion(messages, log_prefix="DASHBOARD_ANALYSIS")
            
            # Extract JSON from response
            dashboard_recommendations = self._extract_json_from_response(raw_response)
            
            if dashboard_recommendations:
                self.logger.info(f"Dashboard analysis results: suitable={dashboard_recommendations.get('is_suitable', False)}")
            else:
                self.logger.warning("Could not extract dashboard recommendations from response")
                dashboard_recommendations = {
                    "is_suitable": False,
                    "reason": "Could not analyze results for dashboard potential"
                }
            
            processing_time = time.time() - start_time
            self.logger.info(f"Dashboard analysis completed in {processing_time:.2f}s")
            
            return dashboard_recommendations
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Dashboard analysis error after {processing_time:.2f}s: {str(e)}", exc_info=True)
            return {
                "is_suitable": False,
                "reason": f"Error analyzing results: {str(e)}"
            }
    
    def _extract_json_from_response(self, content):
        """Extract JSON from model response
        
        Args:
            content (str): The model response content
            
        Returns:
            dict: Extracted JSON object or None if extraction fails
        """
        try:
            # Try to find JSON content using pattern matching
            if '{' in content and '}' in content:
                # Extract content between first { and last }
                json_str = content[content.find('{'):content.rfind('}')+1]
                
                # Parse JSON
                result = json.loads(json_str)
                return result
            
            return None
        except Exception as e:
            self.logger.error(f"Error extracting JSON from response: {str(e)}")
            return None
    
    def close(self):
        """Close the Azure AI client connection"""
        self.logger.info("Closing Azure AI client connection")
        try:
            # Close the LLM Engine instead of directly closing the client
            if hasattr(self, 'llm_engine'):
                self.llm_engine.close()
        except Exception as e:
            self.logger.warning(f"Error closing Azure AI client: {str(e)}")

    # For backward compatibility, expose the client
    @property
    def client(self):
        return self.llm_engine.client