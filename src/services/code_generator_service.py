"""
Code Generator Service

Generates code from data mapping documents using LLM and MCP tools.
This service handles the intelligent code generation workflow:
1. Get mapping details through MCP
2. Extract table names from mapping using LLM
3. Get table structures through MCP
4. Check for existing code
5. Generate new code with all context
6. Save generated code to output directory
"""

import json
import logging
import os
import re
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
from anyio import ClosedResourceError

from src.utils.common_llm import get_llm_engine
from src.utils.mcp_client_manager import MCPClientManager
from src.models.mcp_server import MCPServer
from src.models.mapping_project import MappingProject
from src.models.mapping_document import MappingDocument
from src.models.code_generation_history import CodeGenerationHistory

logger = logging.getLogger('text2sql.code_generator_service')


class CodeGeneratorService:
    """Service for intelligent code generation from data mappings"""
    
    def __init__(self):
        """Initialize the code generator service"""
        self.llm = get_llm_engine()
        
    async def initialize(self):
        """Initialize MCP connections - kept for compatibility but not used"""
        pass
    
    async def _get_dataengineer_client(self):
        """Get a fresh connection to the dataengineer MCP server"""
        try:
            # Import the module-level _mcp_clients dict
            from src.utils.mcp_client_manager import _mcp_clients
            
            # Find dataengineer server
            available_servers = MCPServer.get_all()
            for server in available_servers:
                server_name_lower = server.name.lower()
                if 'data' in server_name_lower and 'engineer' in server_name_lower:
                    # Force cleanup of any stale connections
                    try:
                        # Get existing client if any
                        existing_client = _mcp_clients.get(server.id)
                        if existing_client:
                            try:
                                await existing_client.cleanup()
                                logger.info(f"Cleaned up existing client for {server.name}")
                            except Exception as e:
                                logger.warning(f"Error cleaning up existing client: {e}")
                        
                        # Remove from cache
                        _mcp_clients.pop(server.id, None)
                    except Exception as cleanup_error:
                        logger.warning(f"Error during client cleanup: {cleanup_error}")
                    
                    # Small delay to ensure cleanup
                    import asyncio
                    await asyncio.sleep(0.1)
                    
                    # Get completely fresh client connection
                    client = await MCPClientManager.get_client(server.id, connect=True)
                    if client and client.is_connected():
                        logger.info(f"Connected to dataengineer server: {server.name}")
                        return client
            
            logger.error("Dataengineer MCP server not found or connection failed")
            return None
                
        except Exception as e:
            logger.error(f"Error getting dataengineer client: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _extract_tool_result(self, result) -> str:
        """Extract text content from MCP tool result"""
        try:
            if hasattr(result, 'content') and result.content:
                if hasattr(result.content[0], 'text'):
                    return result.content[0].text
                else:
                    return str(result.content[0])
            else:
                return str(result)
        except (IndexError, AttributeError):
            return str(result)
    
    async def _extract_mapping_info_from_prompt(self, user_prompt: str) -> Dict[str, Any]:
        """Extract mapping name and version number from user prompt using LLM"""
        try:
            prompt = f"""Analyze the following user prompt and extract the mapping name and version number (if mentioned).

User Prompt:
{user_prompt}

Instructions:
1. Extract the mapping name (e.g., "customer_sales", "MAP_ERP_ORDERS_TO_FACT_SALES")
2. Extract the version number if mentioned (e.g., "version 2", "v2", "version 1.5")
3. If no version is mentioned, use null for version_number
4. Return ONLY a JSON object with the format:
   {{"mapping_name": "extracted_name", "version_number": "extracted_version or null"}}

Return only the JSON object, no additional text or explanation.
"""
            
            # Convert prompt to messages format
            messages = [{"role": "user", "content": prompt}]
            response = self.llm.generate_completion(messages)
            
            # Extract content from response
            if hasattr(response, 'choices') and response.choices:
                response_text = response.choices[0].message.content.strip()
            else:
                response_text = str(response).strip()
            
            # Parse JSON response
            import re
            match = re.search(r'\{.*?\}', response_text, re.DOTALL)
            if match:
                json_str = match.group(0)
                extracted_data = json.loads(json_str)
                
                return {
                    "success": True,
                    "mapping_name": extracted_data.get("mapping_name"),
                    "version_number": extracted_data.get("version_number")
                }
            
            return {
                "success": False,
                "error": "Could not parse LLM response"
            }
            
        except Exception as e:
            logger.error(f"Error extracting mapping info from prompt: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_code(self, user_prompt: str, project_name: str, 
                          progress_callback=None, user_id=None, username=None) -> Dict[str, Any]:
        """
        Generate code based on user prompt
        
        Args:
            user_prompt: Natural language prompt from user
            project_name: Name of the project containing the mapping
            progress_callback: Optional callback function to report progress
            user_id: ID of the user triggering the generation
            username: Username of the user triggering the generation
            
        Returns:
            Dictionary with generation results
        """
        operation_id = str(uuid.uuid4())
        start_time = datetime.now()
        history = None
        history_id = None
        mapping_name = None
        
        try:
            # Step 0: Extract mapping name and version from prompt using LLM
            if progress_callback:
                progress_callback("Extracting mapping info from prompt...", 5)
            
            extraction_result = await self._extract_mapping_info_from_prompt(user_prompt)
            if not extraction_result.get("success"):
                return {
                    "success": False,
                    "operation_id": operation_id,
                    "error": f"Failed to extract mapping info: {extraction_result.get('error', 'Unknown error')}"
                }
            
            mapping_name = extraction_result.get("mapping_name")
            version_number = extraction_result.get("version_number")
            
            if not mapping_name:
                return {
                    "success": False,
                    "operation_id": operation_id,
                    "error": "Could not extract mapping name from prompt"
                }
            
            # Send extraction details to progress callback
            if progress_callback:
                progress_callback("Mapping info extracted", 8, "prompt_extraction", {
                    "user_prompt": user_prompt,
                    "mapping_name": mapping_name,
                    "version_number": version_number
                })
            
            # Create history record
            history = CodeGenerationHistory(
                user_id=user_id,
                username=username,
                project_name=project_name,
                mapping_name=mapping_name,
                status='in_progress',
                started_at=start_time.isoformat()
            )
            history_id = history.save()
            
            # Step 1: Get mapping details through MCP
            if progress_callback:
                progress_callback("Fetching mapping details from MCP...", 10)
            
            mapping_result = await self._get_mapping_details(mapping_name, project_name)
            if not mapping_result.get("success"):
                return {
                    "success": False,
                    "operation_id": operation_id,
                    "error": f"Failed to get mapping details: {mapping_result.get('errors', ['Unknown error'])[0]}"
                }
            
            mapping_data = mapping_result.get("mapping_data", [])
            
            # Send mapping details to progress callback
            if progress_callback:
                progress_callback("Mapping details retrieved", 15, "mapping_details", mapping_data)
            
            # Step 2: Extract table names from mapping using LLM
            if progress_callback:
                progress_callback("Extracting table names from mapping...", 25)
            
            table_names = await self._extract_table_names(mapping_data)
            if not table_names:
                return {
                    "success": False,
                    "operation_id": operation_id,
                    "error": "Could not extract table names from mapping data"
                }
            
            # Send table names to progress callback
            if progress_callback:
                progress_callback("Table names extracted", 30, "table_names", {"tables": table_names})
            
            # Step 3: Get table structures through MCP
            if progress_callback:
                progress_callback("Fetching table structures...", 40)
            
            table_structures = await self._get_table_structures(table_names)
            
            # Send table structures to progress callback
            if progress_callback:
                progress_callback("Table structures retrieved", 50, "table_structures", table_structures)
            
            # Step 4: Check for existing code
            if progress_callback:
                progress_callback("Checking for existing code...", 55)
            
            existing_code = await self._get_existing_code(mapping_name, project_name)
            
            # Send existing code to progress callback
            if progress_callback:
                progress_callback("Existing code check completed", 60, "existing_code", existing_code)
            
            # Step 5: Generate code with LLM
            if progress_callback:
                progress_callback("Generating code with AI...", 70)
            
            generated_code = await self._generate_code_with_llm(
                mapping_data=mapping_data,
                table_structures=table_structures,
                existing_code=existing_code,
                mapping_name=mapping_name,
                version_number=version_number,
                progress_callback=progress_callback
            )
            
            if not generated_code.get("success"):
                return {
                    "success": False,
                    "operation_id": operation_id,
                    "error": f"Code generation failed: {generated_code.get('error', 'Unknown error')}"
                }
            
            # Send LLM response to progress callback
            if progress_callback:
                progress_callback("Code generated successfully", 85, "llm_response", {
                    "code_preview": generated_code.get("code", "") ,
                    "success": True
                })
            
            # Step 6: Save generated code
            if progress_callback:
                progress_callback("Saving generated code...", 90)
            
            save_result = await self._save_generated_code(
                code=generated_code.get("code", ""),
                mapping_name=mapping_name,
                project_name=project_name
            )
            
            if not save_result.get("success"):
                return {
                    "success": False,
                    "operation_id": operation_id,
                    "error": f"Failed to save code: {save_result.get('error', 'Unknown error')}"
                }
            
            # Send save result to progress callback
            if progress_callback:
                progress_callback("Code saved successfully", 95, "save_result", {
                    "file_path": save_result.get("file_path", ""),
                    "status": "saved"
                })
            
            if progress_callback:
                progress_callback("Code generation completed!", 100)
            
            # Update history record with success
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            history.status = 'success'
            history.completed_at = end_time.isoformat()
            history.duration_seconds = duration
            history.table_names = table_names
            history.output_file = save_result.get("file_path", "")
            history.code_lines = len(generated_code.get("code", "").split('\n'))
            history.had_existing_code = existing_code is not None
            history.save()
            
            return {
                "success": True,
                "operation_id": operation_id,
                "history_id": history_id,
                "mapping_name": mapping_name,
                "project_name": project_name,
                "code": generated_code.get("code", ""),
                "file_path": save_result.get("file_path", ""),
                "table_names": table_names,
                "had_existing_code": existing_code is not None,
                "timestamp": datetime.now().isoformat(),
                # Step details for UI display
                "mapping_details": mapping_data,
                "table_structures": table_structures,
                "existing_code": existing_code,
                "llm_response": generated_code.get("response_metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Error generating code: {str(e)}")
            
            # Update history record with error (only if it was created)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if history is not None:
                history.status = 'error'
                history.completed_at = end_time.isoformat()
                history.duration_seconds = duration
                history.error_message = str(e)
                history.save()
            
            return {
                "success": False,
                "operation_id": operation_id,
                "history_id": history_id,
                "error": f"Unexpected error: {str(e)}"
            }
    
    async def _get_mapping_details(self, mapping_name: str, project_name: str) -> Dict[str, Any]:
        """Get mapping details using MCP dataengineer tool"""
        try:
            # Get fresh client connection
            client = await self._get_dataengineer_client()
            if not client:
                return {
                    "success": False,
                    "errors": ["Dataengineer MCP server not available"]
                }
            
            result = await client.session.call_tool("get_mapping_details", {
                "mapping_reference_name": mapping_name,
                "project_name": project_name
            })
            
            result_text = self._extract_tool_result(result)
            parsed_result = json.loads(result_text)
            
            # Close the client after use
            try:
                await client.cleanup()
            except:
                pass
            
            return parsed_result
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error getting mapping details: {str(e)}\n{error_details}")
            
            # Try to close client on error
            if 'client' in locals():
                try:
                    await client.cleanup()
                except:
                    pass
            
            return {
                "success": False,
                "errors": [f"Failed to get mapping details: {str(e) or 'Unknown error'}"]
            }
    
    async def _extract_table_names(self, mapping_data: List[Dict[str, Any]]) -> List[str]:
        """Extract unique table names from mapping data using LLM"""
        try:
            # Prepare mapping data as text for LLM
            mapping_text = json.dumps(mapping_data, indent=2)
            
            prompt = f"""Analyze the following data mapping document and extract all unique table names used in the mapping.

Mapping Data:
{mapping_text}

Instructions:
1. Look for table names in the 'definition' field where 'type' is 'Table'
2. Look for table names in 'Full Table Name / Subquery Definition' field
3. Extract only actual table names, not aliases or subqueries
4. Return ONLY a JSON array of unique table names
5. Format: ["table1", "table2", "table3"]

Return only the JSON array, no additional text or explanation.
"""
            
            # Convert prompt to messages format for generate_completion
            messages = [{"role": "user", "content": prompt}]
            response = self.llm.generate_completion(messages)
            
            # Extract content from response
            if hasattr(response, 'choices') and response.choices:
                response_text = response.choices[0].message.content
            else:
                response_text = str(response)
            
            # Parse LLM response - manually extract JSON array
            response_text = response_text.strip()
            
            # Try to find JSON array in the response
            match = re.search(r'\[.*?\]', response_text, re.DOTALL)
            if match:
                json_str = match.group(0)
                table_names = json.loads(json_str)
                
                # Validate and clean
                if isinstance(table_names, list):
                    # Remove duplicates and empty strings
                    table_names = list(set([t.strip() for t in table_names if t and isinstance(t, str)]))
                    logger.info(f"Extracted {len(table_names)} table names: {table_names}")
                    return table_names
            
            # Fallback: try to extract from mapping_data directly
            table_names = set()
            for record in mapping_data:
                if record.get('type') == 'Table':
                    definition = record.get('definition', '')
                    if definition and not definition.upper().startswith('SELECT'):
                        table_names.add(definition.strip())
            
            return list(table_names)
            
        except Exception as e:
            logger.error(f"Error extracting table names: {str(e)}")
            # Fallback to direct extraction
            table_names = set()
            for record in mapping_data:
                if record.get('type') == 'Table':
                    definition = record.get('definition', '')
                    if definition and not definition.upper().startswith('SELECT'):
                        table_names.add(definition.strip())
            return list(table_names)
    
    async def _get_table_structures(self, table_names: List[str]) -> Dict[str, Any]:
        """Get table structures using MCP dataengineer tool"""
        structures = {}
        client = None
        
        try:
            # Get fresh client connection
            client = await self._get_dataengineer_client()
            if not client:
                logger.error("Cannot get table structures - dataengineer client not available")
                return {table_name: {"columns": [], "status": "error", "error": "MCP client not available"} 
                        for table_name in table_names}
            
            # Validate client connection before proceeding
            if not client.is_connected():
                logger.error("Client connection validation failed - not connected")
                return {table_name: {"columns": [], "status": "error", "error": "MCP client not connected"} 
                        for table_name in table_names}
            
            # Validate that session exists
            if not hasattr(client, 'session') or client.session is None:
                logger.error("Client session is not available")
                return {table_name: {"columns": [], "status": "error", "error": "MCP client session not available"} 
                        for table_name in table_names}
            
            for table_name in table_names:
                try:
                    # Double-check connection before each call
                    if not client.is_connected() or not client.session:
                        logger.error(f"Connection lost before processing {table_name}")
                        structures[table_name] = {
                            "columns": [],
                            "status": "error",
                            "error": "Connection lost"
                        }
                        continue
                    
                    # Get table columns
                    result = await client.session.call_tool("get_table_data", {
                        "table_name": table_name,
                        "limit": 0  # We only need column names, not data
                    })
                    
                    result_text = self._extract_tool_result(result)
                    table_info = json.loads(result_text)
                    
                    if table_info.get("success"):
                        structures[table_name] = {
                            "columns": table_info.get("columns", []),
                            "status": "found"
                        }
                    else:
                        structures[table_name] = {
                            "columns": [],
                            "status": "not_found",
                            "error": table_info.get("errors", ["Unknown error"])
                        }
                        
                except Exception as e:
                    logger.error(f"Error getting structure for {table_name}: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    structures[table_name] = {
                        "columns": [],
                        "status": "error",
                        "error": str(e)
                    }
        finally:
            # Always close the client
            if client:
                try:
                    await client.cleanup()
                except Exception as cleanup_error:
                    logger.warning(f"Error during client cleanup: {cleanup_error}")
        
        return structures
    
    async def _get_existing_code(self, mapping_name: str, project_name: str) -> Optional[str]:
        """Check if code already exists for this mapping"""
        try:
            # Construct output directory path
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            output_dir = os.path.join(base_dir, 'uploads', 'projects', project_name, 'sql')
            
            # Look for file with mapping name
            safe_filename = self._sanitize_filename(mapping_name)
            sql_file_path = os.path.join(output_dir, f"{safe_filename}.sql")
            
            if os.path.exists(sql_file_path):
                with open(sql_file_path, 'r') as f:
                    existing_code = f.read()
                logger.info(f"Found existing code for {mapping_name}")
                return existing_code
            else:
                logger.info(f"No existing code found for {mapping_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error checking for existing code: {str(e)}")
            return None
    
    async def _generate_code_with_llm(self, mapping_data: List[Dict], 
                                     table_structures: Dict[str, Any],
                                     existing_code: Optional[str],
                                     mapping_name: str,
                                     version_number: Optional[str],
                                     progress_callback=None) -> Dict[str, Any]:
        """Generate code using LLM with all available context"""
        try:
            # Prepare context
            mapping_text = json.dumps(mapping_data, indent=2)
            structures_text = json.dumps(table_structures, indent=2)
            
            version_section = ""
            if version_number:
                version_section = f"\n## Version: {version_number}\n"
            
            existing_code_section = ""
            if existing_code:
                existing_code_section = f"""
## Existing Code (for reference and improvement):
```sql
{existing_code}
```

NOTE: Review the existing code and improve it if needed, or generate new code if the existing code is not suitable.
"""
            
            prompt = f"""You are an expert SQL developer. Generate production-quality SQL code based on the following data mapping specification.

## Mapping Name: {mapping_name}{version_section}

## Mapping Details:
{mapping_text}

## Table Structures:
{structures_text}

{existing_code_section}

## Instructions:
1. Analyze the mapping data to understand the transformation requirements
2. Generate a complete SQL script (SELECT statement, stored procedure, or ETL script as appropriate)
3. Include proper JOINs based on the mapping specifications
4. Apply all transformation logic specified in the mapping
5. Handle NULL values and data type conversions appropriately
6. Add comments explaining complex logic
7. Follow SQL best practices and optimize for performance
8. If existing code is provided, improve it or generate new code if needed
{f'9. Consider version {version_number} requirements and optimizations' if version_number else ''}

## Requirements:
- The code should be production-ready
- Include proper error handling where appropriate
- Use meaningful aliases for tables
- Format the code for readability
- Add a header comment with mapping name{f' and version {version_number}' if version_number else ''} and generation timestamp

Return ONLY the SQL code, properly formatted. Do not include any explanations or markdown formatting.
Start with: -- Generated Code for {mapping_name}{f' (Version {version_number})' if version_number else ''}
"""
            
            # Send prompt to progress callback for display
            if progress_callback:
                progress_callback("Prompt sent to LLM", 72, "llm_prompt", {
                    "prompt": prompt,
                    "prompt_length": len(prompt),
                    "timestamp": datetime.now().isoformat()
                })
            
            # Convert prompt to messages format
            messages = [{"role": "user", "content": prompt}]
            response = self.llm.generate_completion(messages)
            
            # Extract content from response
            if hasattr(response, 'choices') and response.choices:
                code = response.choices[0].message.content.strip()
            else:
                code = str(response).strip()
            
            # Remove markdown code blocks if present
            if code.startswith('```'):
                lines = code.split('\n')
                # Remove first line if it's ```sql or ```
                if lines[0].startswith('```'):
                    lines = lines[1:]
                # Remove last line if it's ```
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                code = '\n'.join(lines)
            
            # Ensure header comment is present
            if not code.startswith('--'):
                header = f"-- Generated Code for {mapping_name}\n-- Generated at: {datetime.now().isoformat()}\n\n"
                code = header + code
            
            logger.info(f"Generated {len(code)} characters of code for {mapping_name}")
            
            return {
                "success": True,
                "code": code
            }
            
        except Exception as e:
            logger.error(f"Error generating code with LLM: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _save_generated_code(self, code: str, mapping_name: str, 
                                  project_name: str) -> Dict[str, Any]:
        """Save generated code to output directory"""
        try:
            # Construct output directory path
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            output_dir = os.path.join(base_dir, 'uploads', 'projects', project_name, 'sql')
            
            # Create directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate safe filename
            safe_filename = self._sanitize_filename(mapping_name)
            sql_file_path = os.path.join(output_dir, f"{safe_filename}.sql")
            
            # Write code to file
            with open(sql_file_path, 'w') as f:
                f.write(code)
            
            logger.info(f"Saved generated code to {sql_file_path}")
            
            return {
                "success": True,
                "file_path": sql_file_path
            }
            
        except Exception as e:
            logger.error(f"Error saving generated code: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to remove invalid characters"""
        # Replace spaces with underscores
        filename = filename.replace(' ', '_')
        # Remove any character that's not alphanumeric, underscore, or hyphen
        filename = re.sub(r'[^\w\-]', '', filename)
        # Limit length
        filename = filename[:100]
        return filename
    
    async def list_projects(self) -> List[Dict[str, Any]]:
        """List all available projects"""
        try:
            MappingProject.create_table()
            projects = MappingProject.get_all()
            return [p.to_dict() for p in projects]
        except Exception as e:
            logger.error(f"Error listing projects: {str(e)}")
            return []
    
    async def list_mappings(self, project_name: Optional[str] = None) -> List[str]:
        """List available mappings from the mapping file"""
        try:
            # Get fresh client connection
            client = await self._get_dataengineer_client()
            if not client:
                logger.error("Dataengineer MCP client not available")
                return []
            
            result = await client.session.call_tool("list_mappings", {})
            result_text = self._extract_tool_result(result)
            mapping_result = json.loads(result_text)
            
            if mapping_result.get("success"):
                return mapping_result.get("mappings", [])
            else:
                logger.error(f"Error listing mappings: {mapping_result.get('errors')}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing mappings: {str(e)}")
            return []
