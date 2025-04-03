from src.utils.schema_manager import SchemaManager
from src.utils.llm_engine import LLMEngine
from azure.ai.inference.models import SystemMessage, UserMessage
import logging
import time
import json

class IntentAgent:
    """Agent for detecting the intent of user's natural language query"""
    
    def __init__(self):
        """Initialize the intent agent"""
        self.llm_engine = LLMEngine()
        self.schema_manager = SchemaManager()
        self.logger = logging.getLogger('text2sql.agents.intent')
        
    def detect_intent(self, query):
        """Detect the intent of a natural language query
        
        Args:
            query (str): The natural language query from the user
            
        Returns:
            dict: Dictionary with intent classification and confidence score
        """
        start_time = time.time()
        self.logger.info(f"Intent detection started for query: '{query}'")
        
        # Define possible intents
        intent_types = [
            "data_retrieval",     # User wants to retrieve data (generate SQL query)
            "schema_exploration", # User wants to explore database schema
            "metadata_request",   # User wants information about the database itself
            "general_question"    # General question not related to SQL generation
        ]
        
        # Default to data_retrieval intent without calling LLM
        self.logger.info("Using default intent 'data_retrieval' without calling LLM")
        result = {"intent": "data_retrieval", "confidence": 1.0}
        processing_time = time.time() - start_time
        self.logger.info(f"Intent detection completed in {processing_time:.2f}s")
        return result
        
    def determine_relevant_workspaces(self, query, workspaces):
        """Determine which workspace(s) are relevant for the user's query
        
        Args:
            query (str): The natural language query from the user
            workspaces (list): List of workspace dictionaries
            
        Returns:
            list: List of relevant workspace names
        """
        start_time = time.time()
        self.logger.info(f"Workspace selection started for query: '{query}'")
        self.logger.info(f"Available workspaces: {json.dumps([w['name'] for w in workspaces])}")
        
        if not workspaces:
            self.logger.warning("No workspaces available for selection")
            return []
            
        # If only one workspace exists, use it
        if len(workspaces) == 1:
            workspace_name = workspaces[0]["name"]
            self.logger.info(f"Only one workspace available, selecting: {workspace_name}")
            return [workspace_name]
        
        # Get table information for each workspace for better context
        workspace_info = []
        for workspace in workspaces:
            tables = self.schema_manager.get_tables(workspace["name"])
            table_info = []
            for table in tables:
                table_info.append(f"- {table['name']}: {table.get('description', 'No description')}")
            
            workspace_text = (
                f"{workspace['name']}:\n"
                f"Description: {workspace.get('description', 'No description')}\n"
                f"Tables:\n" + "\n".join(table_info)
            )
            workspace_info.append(workspace_text)
            
        workspace_descriptions = "\n\n".join(workspace_info)
            
        messages = [
            SystemMessage("""You are a workspace selection agent for a Text-to-SQL system.
Your job is to determine which workspace(s) are most relevant to a user query.
You will be given detailed information about each workspace including their tables.
Return ONLY the names of relevant workspaces, separated by commas if there are multiple.
Choose workspaces that contain the tables and data needed to answer the query.
Do not include any other text in your response."""),
            UserMessage(f"Available workspaces:\n{workspace_descriptions}\n\nUser query: {query}")
        ]
        
        try:
            self.logger.info("Sending request to AI model for workspace selection")
            
            # Use LLMEngine for centralized LLM interaction
            raw_response = self.llm_engine.generate_completion(messages, log_prefix="WORKSPACE")
            raw_response = raw_response.strip()
            self.logger.info(f"Raw model response: '{raw_response}'")
            
            workspace_names = raw_response.split(",")
            workspace_names = [w.strip() for w in workspace_names]
            
            # Validate the workspace names
            valid_names = set(w["name"] for w in workspaces)
            original_count = len(workspace_names)
            workspace_names = [w for w in workspace_names if w in valid_names]
            filtered_count = len(workspace_names)
            
            if original_count != filtered_count:
                self.logger.warning(f"Model suggested {original_count - filtered_count} invalid workspaces that were filtered out")
            
            if not workspace_names:
                self.logger.warning("No valid workspaces selected, defaulting to first workspace")
                result = [workspaces[0]["name"]]
            else:
                result = workspace_names
            
            processing_time = time.time() - start_time
            self.logger.info(f"Workspace selection completed in {processing_time:.2f}s. Selected: {', '.join(result)}")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Workspace selection error after {processing_time:.2f}s: {str(e)}", exc_info=True)
            # Default to first workspace on error
            result = [workspaces[0]["name"]]
            self.logger.warning(f"Defaulting to first workspace due to error: {result[0]}")
            return result
            
    def close(self):
        """Close the AI client connection"""
        self.logger.info("Closing intent agent's LLM engine connection")
        self.llm_engine.close()