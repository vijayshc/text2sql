"""
Autogen Team & Agent Workflow Integration for Finch Database Agent
Implements multi-agent collaboration for database intelligence tasks

This module integrates the Finch MCP server with Autogen's team-based workflow
to create a sophisticated multi-agent system for database analysis and insights.

Architecture:
1. Supervisor Agent - Orchestrates the workflow
2. Database Agent - Handles database operations via Finch MCP
3. Analyst Agent - Performs data analysis and interpretation
4. Report Agent - Generates summaries and reports

Inspired by Uber's Finch architecture with multi-agent orchestration.
"""

import json
import logging
import asyncio
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

# Autogen imports
try:
    import autogen
    from autogen import ConversableAgent, GroupChat, GroupChatManager
    from autogen.coding import LocalCommandLineCodeExecutor
except ImportError:
    print("Autogen not installed. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogen"])
    import autogen
    from autogen import ConversableAgent, GroupChat, GroupChatManager
    from autogen.coding import LocalCommandLineCodeExecutor

# MCP Client imports
sys.path.append('/home/vijay/gitrepo/copilot/text2sql')
from src.utils.mcp_client import MCPClient
from src.utils.common_llm import get_llm_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('finch_autogen_workflow')

class FinchAutogenWorkflow:
    """Main orchestrator for Finch database intelligence with Autogen teams"""
    
    def __init__(self):
        self.mcp_client = None
        self.llm_config = None
        self.agents = {}
        self.group_chat = None
        self.manager = None
        self.initialize()
    
    def initialize(self):
        """Initialize the autogen workflow with MCP client and agents"""
        try:
            # Setup LLM configuration for Autogen
            self.llm_config = self._setup_llm_config()
            
            # Initialize MCP client for Finch server
            self.mcp_client = MCPClient()
            
            # Create specialized agents
            self._create_agents()
            
            # Setup group chat
            self._setup_group_chat()
            
            logger.info("Finch Autogen Workflow initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Finch workflow: {str(e)}")
            raise
    
    def _setup_llm_config(self) -> Dict[str, Any]:
        """Setup LLM configuration for Autogen agents"""
        try:
            # Get LLM configuration from existing common_llm
            llm_engine = get_llm_engine()
            
            # Configure for Autogen
            config = {
                "config_list": [
                    {
                        "model": "gpt-4o-mini",  # or your preferred model
                        "api_key": os.getenv("OPENROUTER_API_KEY"),
                        "base_url": "https://openrouter.ai/api/v1",
                        "api_type": "openai"
                    }
                ],
                "temperature": 0.1,
                "timeout": 120
            }
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to setup LLM config: {str(e)}")
            # Fallback configuration
            return {
                "config_list": [
                    {
                        "model": "gpt-4o-mini",
                        "api_key": "dummy_key",
                        "base_url": "http://localhost:1234/v1",
                        "api_type": "openai"
                    }
                ],
                "temperature": 0.1
            }
    
    def _create_agents(self):
        """Create specialized agents for the database intelligence workflow"""
        
        # Supervisor Agent - Orchestrates the entire workflow
        self.agents['supervisor'] = ConversableAgent(
            name="Database_Supervisor",
            system_message="""You are the Database Intelligence Supervisor Agent.
            
Your role is to:
1. Understand user requests for database analysis
2. Orchestrate the team of specialist agents
3. Ensure proper workflow execution
4. Coordinate between Database, Analyst, and Report agents
5. Validate results and ensure quality

You should break down complex requests into manageable tasks and delegate to appropriate agents.
When a user asks for database insights, coordinate with:
- Database_Agent for data retrieval and queries
- Data_Analyst for analysis and interpretation  
- Report_Generator for final summaries and visualizations

Always ensure the workflow is logical and that each agent contributes their expertise.""",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False
        )
        
        # Database Agent - Handles database operations via Finch MCP
        self.agents['database'] = ConversableAgent(
            name="Database_Agent",
            system_message="""You are the Database Agent specialized in database operations.

Your capabilities include:
1. Searching database metadata using semantic understanding
2. Generating SQL queries from natural language
3. Executing queries safely with validation
4. Retrieving database schema information
5. Validating SQL for safety and syntax

You have access to the Finch MCP server with these tools:
- get_database_schema: Get schema information
- search_metadata: Search for relevant tables/columns
- generate_sql: Convert natural language to SQL
- execute_query: Execute SQL safely
- query_and_analyze: End-to-end query workflow
- validate_sql: Validate queries before execution

When asked to work with database data:
1. First search metadata to understand the request
2. Generate appropriate SQL queries
3. Validate queries for safety
4. Execute and return results
5. Provide clear explanations of what was done

Always prioritize data security and never execute dangerous operations.""",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False
        )
        
        # Data Analyst Agent - Performs analysis and interpretation
        self.agents['analyst'] = ConversableAgent(
            name="Data_Analyst",
            system_message="""You are the Data Analyst Agent specialized in data interpretation and insights.

Your role is to:
1. Analyze query results and data patterns
2. Identify trends, anomalies, and business insights
3. Perform statistical analysis when appropriate
4. Suggest follow-up questions or additional analysis
5. Interpret business meaning from raw data

When you receive data from the Database_Agent:
1. Examine the structure and content
2. Calculate relevant statistics and metrics
3. Identify key insights and patterns
4. Suggest business implications
5. Recommend additional analysis if needed

You should work closely with the Database_Agent to request additional data when needed
and with the Report_Generator to ensure insights are properly communicated.""",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False
        )
        
        # Report Generator Agent - Creates summaries and reports
        self.agents['reporter'] = ConversableAgent(
            name="Report_Generator",
            system_message="""You are the Report Generator Agent specialized in creating clear, actionable reports.

Your responsibilities include:
1. Synthesizing findings from Database and Analyst agents
2. Creating structured, professional reports
3. Highlighting key insights and recommendations
4. Formatting results for easy consumption
5. Generating executive summaries when needed

Your reports should include:
1. Executive Summary (key findings in 2-3 sentences)
2. Data Sources (tables/queries used)
3. Key Findings (insights from analysis)
4. Recommendations (actionable next steps)
5. Technical Details (methodology and assumptions)

Make reports clear for both technical and business audiences.
Focus on business value and actionable insights.""",
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            code_execution_config=False
        )
        
        # User Proxy for human interaction
        self.agents['user_proxy'] = ConversableAgent(
            name="User_Proxy",
            system_message="You represent the user and coordinate with the agent team to fulfill database intelligence requests.",
            llm_config=False,  # No LLM needed for user proxy
            human_input_mode="NEVER",
            code_execution_config=False
        )
    
    def _setup_group_chat(self):
        """Setup group chat with proper agent coordination"""
        
        # Define agent list
        agent_list = [
            self.agents['user_proxy'],
            self.agents['supervisor'], 
            self.agents['database'],
            self.agents['analyst'],
            self.agents['reporter']
        ]
        
        # Create group chat
        self.group_chat = GroupChat(
            agents=agent_list,
            messages=[],
            max_round=20,  # Limit conversation rounds
            speaker_selection_method="auto",
            allow_repeat_speaker=False
        )
        
        # Create group chat manager
        self.manager = GroupChatManager(
            groupchat=self.group_chat,
            llm_config=self.llm_config,
            system_message="""You are the Group Chat Manager for the Database Intelligence Team.

Your role is to facilitate smooth communication between agents and ensure productive workflow.

Agent capabilities:
- Database_Supervisor: Orchestrates workflow and coordinates agents
- Database_Agent: Handles database operations and queries via Finch MCP
- Data_Analyst: Analyzes data and provides insights
- Report_Generator: Creates professional reports and summaries

Ensure each agent contributes their expertise and the workflow progresses logically toward the user's goal."""
        )
    
    async def start_finch_mcp_server(self) -> bool:
        """Start the Finch MCP server process"""
        try:
            # Start Finch MCP server as subprocess
            server_command = [
                sys.executable,
                "/home/vijay/gitrepo/copilot/text2sql/src/services/mcp_finch_server.py"
            ]
            
            self.finch_process = subprocess.Popen(
                server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give server time to start
            await asyncio.sleep(2)
            
            # Test connection
            if self.finch_process.poll() is None:
                logger.info("Finch MCP server started successfully")
                return True
            else:
                logger.error("Finch MCP server failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start Finch MCP server: {str(e)}")
            return False
    
    async def setup_mcp_connection(self) -> bool:
        """Setup MCP connection to Finch server"""
        try:
            # Configure MCP client for stdio connection
            await self.mcp_client.connect(
                server_type="stdio",
                command=[
                    sys.executable,
                    "/home/vijay/gitrepo/copilot/text2sql/src/services/mcp_finch_server.py"
                ]
            )
            
            # Test connection by listing tools
            tools = await self.mcp_client.list_tools()
            logger.info(f"Connected to Finch MCP server with {len(tools)} tools")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup MCP connection: {str(e)}")
            return False
    
    def register_mcp_tools_with_database_agent(self):
        """Register MCP tools with the Database Agent"""
        try:
            # Create MCP tool functions for the Database Agent
            async def call_mcp_tool(tool_name: str, **kwargs) -> str:
                """Call MCP tool and return results"""
                try:
                    result = await self.mcp_client.call_tool(tool_name, kwargs)
                    return json.dumps(result, indent=2)
                except Exception as e:
                    return f"Error calling {tool_name}: {str(e)}"
            
            # Register specific tools
            finch_tools = [
                "get_database_schema",
                "search_metadata", 
                "generate_sql",
                "execute_query",
                "query_and_analyze",
                "validate_sql",
                "export_results_csv",
                "get_catalog_overview"
            ]
            
            # Add tools to Database Agent's function map
            for tool_name in finch_tools:
                self.agents['database'].register_function(
                    function_map={
                        tool_name: lambda **kwargs, tn=tool_name: asyncio.run(call_mcp_tool(tn, **kwargs))
                    }
                )
            
            logger.info("MCP tools registered with Database Agent")
            
        except Exception as e:
            logger.error(f"Failed to register MCP tools: {str(e)}")
    
    async def process_database_request(self, user_request: str) -> Dict[str, Any]:
        """Process a database intelligence request through the agent team"""
        try:
            # Ensure MCP connection is ready
            if not self.mcp_client or not self.mcp_client.connected:
                await self.setup_mcp_connection()
            
            # Initialize conversation
            initial_message = f"""Database Intelligence Request: {user_request}

Please work as a team to fulfill this request:

1. Database_Supervisor: Analyze the request and orchestrate the workflow
2. Database_Agent: Use Finch MCP tools to retrieve and query data
3. Data_Analyst: Analyze the results and extract insights  
4. Report_Generator: Create a comprehensive report

Begin the collaborative workflow to address this request."""
            
            # Start group chat
            chat_result = self.agents['user_proxy'].initiate_chat(
                self.manager,
                message=initial_message,
                max_turns=15
            )
            
            # Extract results from conversation
            conversation_history = []
            for message in self.group_chat.messages:
                conversation_history.append({
                    'speaker': message.get('name', 'Unknown'),
                    'content': message.get('content', ''),
                    'timestamp': datetime.now().isoformat()
                })
            
            # Generate workflow summary
            workflow_result = {
                'request': user_request,
                'status': 'completed',
                'conversation_history': conversation_history,
                'agents_involved': list(self.agents.keys()),
                'total_messages': len(conversation_history),
                'timestamp': datetime.now().isoformat()
            }
            
            # Extract final report from last reporter message
            for message in reversed(conversation_history):
                if message['speaker'] == 'Report_Generator':
                    workflow_result['final_report'] = message['content']
                    break
            
            return workflow_result
            
        except Exception as e:
            logger.error(f"Error processing database request: {str(e)}")
            return {
                'request': user_request,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def test_workflow(self) -> Dict[str, Any]:
        """Test the workflow with a sample request"""
        test_request = "Show me the top 5 customers by order value and analyze their purchasing patterns"
        
        logger.info("Testing Finch Autogen workflow...")
        result = await self.process_database_request(test_request)
        
        return result
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if hasattr(self, 'mcp_client') and self.mcp_client:
                asyncio.run(self.mcp_client.disconnect())
            
            if hasattr(self, 'finch_process') and self.finch_process:
                self.finch_process.terminate()
                self.finch_process.wait()
            
            logger.info("Finch workflow cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")


async def main():
    """Main entry point for testing the Finch Autogen workflow"""
    workflow = None
    
    try:
        # Initialize workflow
        workflow = FinchAutogenWorkflow()
        
        # Setup MCP connection
        connection_success = await workflow.setup_mcp_connection()
        
        if not connection_success:
            print("Failed to connect to Finch MCP server")
            return
        
        # Register tools
        workflow.register_mcp_tools_with_database_agent()
        
        # Test workflow
        print("\n=== Testing Finch Autogen Workflow ===\n")
        
        test_result = await workflow.test_workflow()
        
        print("\n=== Workflow Results ===\n")
        print(json.dumps(test_result, indent=2, default=str))
        
        # Interactive mode
        print("\n=== Interactive Mode ===")
        print("Enter database intelligence requests (type 'quit' to exit):\n")
        
        while True:
            user_input = input("Request: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if user_input:
                print("\nProcessing request...")
                result = await workflow.process_database_request(user_input)
                
                if 'final_report' in result:
                    print("\n=== Final Report ===")
                    print(result['final_report'])
                else:
                    print("\n=== Workflow Result ===")
                    print(json.dumps(result, indent=2, default=str))
                
                print("\n" + "="*50 + "\n")
        
    except KeyboardInterrupt:
        print("\nWorkflow interrupted by user")
    except Exception as e:
        print(f"Workflow error: {str(e)}")
        logger.error(f"Main workflow error: {str(e)}")
    finally:
        if workflow:
            workflow.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
