from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
import json
import sys
import logging
import time
from config.config import AZURE_ENDPOINT, AZURE_MODEL_NAME, GITHUB_TOKEN, MAX_TOKENS, TEMPERATURE

class AzureAIClient:
    def __init__(self):
        """Initialize the Azure AI Client with the GitHub token for authentication"""
        self.logger = logging.getLogger('text2sql.azure')
        
        if not GITHUB_TOKEN:
            self.logger.critical("GITHUB_TOKEN environment variable not set")
            print("Error: GITHUB_TOKEN environment variable not set")
            sys.exit(1)
            
        self.logger.info(f"Initializing Azure AI Client with endpoint: {AZURE_ENDPOINT}")
        self.logger.info(f"Using model: {AZURE_MODEL_NAME}")
        
        try:
            self.client = ChatCompletionsClient(
                endpoint=AZURE_ENDPOINT,
                credential=AzureKeyCredential(GITHUB_TOKEN),
            )
            self.model_name = AZURE_MODEL_NAME
            self.logger.info("Azure AI Client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Azure AI Client: {str(e)}", exc_info=True)
            raise
    
    def generate_sql(self, query, schema=None, examples=None):
        """Generate SQL from a natural language query
        
        Args:
            query (str): The natural language query
            schema (str, optional): The database schema information
            examples (list, optional): Example queries and corresponding SQL
            
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
4. Use appropriate JOIN conditions based on primary/foreign key relationships
5. Include a brief explanation of your query

Rules:
- Include table names and column references exactly as provided in the schema
- Use appropriate SQL functions based on column data types
- Consider NULL values in your conditions
- Use table aliases for better readability when joining multiple tables
- Add column aliases for computed values
- Format the SQL query with proper indentation
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
            self.logger.debug(f"Including schema information ({schema_length} chars)")
            messages.append(UserMessage(f"Here's the database schema:\n{schema}"))
        else:
            self.logger.debug("No schema information provided")
        
        # Add examples if provided
        if examples and len(examples) > 0:
            self.logger.debug(f"Including {len(examples)} SQL examples")
            example_text = "Here are some example queries and their SQL:\n"
            for example in examples:
                example_text += f"Question: {example['question']}\nSQL: {example['sql']}\n\n"
            messages.append(UserMessage(example_text))
        else:
            self.logger.debug("No SQL examples provided")
        
        # Add the user query
        messages.append(UserMessage(f"Convert this question to SQL: {query}"))
        
        # Log the prompt message but truncate if too large
        prompt_str = str([m.content for m in messages])
        if len(prompt_str) > 500:
            self.logger.debug(f"SQL generation prompt: {prompt_str[:500]}... (truncated)")
        else:
            self.logger.debug(f"SQL generation prompt: {prompt_str}")
        
        try:
            self.logger.debug(f"Sending request to {self.model_name} with max_tokens={MAX_TOKENS}, temperature={TEMPERATURE}")
            call_start = time.time()
            
            response = self.client.complete(
                model=self.model_name,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE
            )
            
            call_duration = time.time() - call_start
            self.logger.debug(f"Model response received in {call_duration:.2f}s")
            
            # Extract SQL from the response
            raw_response = response.choices[0].message.content
            # Log truncated response if large
            if len(raw_response) > 500:
                self.logger.debug(f"Raw model response: '{raw_response[:500]}...' (truncated)")
            else:
                self.logger.debug(f"Raw model response: '{raw_response}'")
                
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
        self.logger.debug("Parsing SQL from model response")
        # Simple extraction for SQL code blocks
        sql = ""
        explanation = ""
        
        # Check if content contains a SQL code block
        if "```sql" in content:
            self.logger.debug("Found SQL code block in response")
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
                
                self.logger.debug(f"Extracted SQL query ({len(sql)} chars) and explanation ({len(explanation)} chars)")
        else:
            # Fallback if no code block formatting
            self.logger.debug("No SQL code block found, using entire response as SQL")
            sql = content
            explanation = "No specific explanation provided by the model."
        
        return {
            "sql": sql,
            "explanation": explanation,
            "raw_response": content
        }
    
    def close(self):
        """Close the Azure AI client connection"""
        self.logger.debug("Closing Azure AI client connection")
        try:
            self.client.close()
        except Exception as e:
            self.logger.warning(f"Error closing Azure AI client: {str(e)}")