"""
AI Data Mapping Analyst Agent

This agent implements the cognitive workflow that orchestrates the MCP tool calls
to intelligently analyze, map, and model data for enterprise data warehouses.
It replicates the workflow of an expert data architect.
"""

import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

from src.utils.common_llm import get_llm_engine

logger = logging.getLogger('text2sql.data_mapping_agent')


class MappingStatus(Enum):
    """Status enumeration for mapping operations"""
    SUCCESS = "success"
    SUCCESS_WITH_AGGREGATION = "success_with_aggregation"
    REQUIRES_NEW_TABLE = "requires_new_table"
    FAILED_NO_PATH = "failed_no_path"
    FAILED_NO_MATCH = "failed_no_match"
    ERROR = "error"


class DataMappingAgent:
    """
    AI agent that orchestrates data mapping and modeling operations
    using the MCP Data Mapping Analyst server tools.
    """
    
    def __init__(self, mcp_client=None):
        """
        Initialize the Data Mapping Agent
        
        Args:
            mcp_client: MCP client instance for calling data mapping tools
        """
        self.mcp_client = mcp_client
        self.llm = get_llm_engine()
        self.operation_log = []
    
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
        
    async def test_connection(self) -> Dict[str, Any]:
        """Test the MCP server connection"""
        if not self.mcp_client:
            return {
                "status": "error",
                "message": "No MCP client available"
            }
        
        try:
            # Check if client is connected and has a session
            if not self.mcp_client.is_connected() or not self.mcp_client.session:
                # Attempt to connect if not already connected
                await self.mcp_client.connect()
                if not self.mcp_client.is_connected() or not self.mcp_client.session:
                    return {
                        "status": "error",
                        "message": "MCP client is not connected"
                    }
            
            # Try to call the catalog overview tool using the session
            result = await self.mcp_client.session.call_tool("get_catalog_overview", {})
            result_content = self._extract_tool_result(result)
            
            return {
                "status": "success",
                "message": "MCP server connection successful",
                "tools_available": True,
                "test_result": result_content[:200] + "..." if len(result_content) > 200 else result_content
            }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"MCP connection test failed: {str(e)}"
            }
    
    async def map_column(self, source_table: str, source_column: str, 
                        target_table: str = None, target_column: str = None,
                        user_context: str = "") -> Dict[str, Any]:
        """
        Main entry point for column mapping analysis.
        Implements the complete cognitive workflow for data mapping.
        
        Args:
            source_table: Name of the source table
            source_column: Name of the source column
            target_table: Optional target table name (if known)
            target_column: Optional target column name (if known)
            user_context: Additional context about the mapping requirement
            
        Returns:
            Dictionary with mapping analysis results
        """
        
        self.operation_log = []
        operation_id = str(uuid.uuid4())
        
        logger.info(f"Starting column mapping analysis: {source_table}.{source_column}")
        self._log_operation("INITIATION", f"Starting mapping for {source_table}.{source_column}")
        
        try:
            # Step 1: Check for existing mapping
            if target_table and target_column:
                existing_mapping = await self._check_existing_mapping(target_table, target_column)
                if existing_mapping.get("status") == "found":
                    self._log_operation("CACHE_HIT", "Found existing mapping")
                    return {
                        "operation_id": operation_id,
                        "status": MappingStatus.SUCCESS.value,
                        "result_type": "existing_mapping",
                        "mapping": existing_mapping["mapping"],
                        "operations_log": self.operation_log
                    }
            
            # Step 2: Analyze source column
            source_analysis = await self._analyze_source_column(source_table, source_column)
            if source_analysis.get("status") == "error":
                return self._build_error_result(operation_id, "Failed to analyze source column", source_analysis)
            
            column_profile = source_analysis.get("column_profile", {})
            subject_area = source_analysis.get("table_context", {}).get("subject_area")
            
            if not subject_area:
                return self._build_error_result(operation_id, "Could not determine subject area for source column")
            
            # Step 3: Find candidate tables
            candidates = await self._find_candidate_tables(subject_area)
            if candidates.get("status") == "no_results":
                # Propose new table if no candidates found
                return await self._propose_new_table_solution(operation_id, source_analysis, user_context)
            
            candidate_tables = candidates.get("tables", [])
            
            # Step 4: Analyze granularity fit and prioritize candidates
            direct_fit_tables, aggregation_tables, mismatch_tables = await self._analyze_candidates_granularity(
                source_table, candidate_tables
            )
            
            # Step 5: Try direct fit candidates first
            if direct_fit_tables:
                result = await self._process_direct_fit_candidates(
                    operation_id, source_analysis, direct_fit_tables, target_table, target_column
                )
                if result["status"] != MappingStatus.FAILED_NO_MATCH.value:
                    return result
            
            # Step 6: Try aggregation candidates if direct fit failed
            if aggregation_tables:
                result = await self._process_aggregation_candidates(
                    operation_id, source_analysis, aggregation_tables, target_table, target_column
                )
                if result["status"] != MappingStatus.FAILED_NO_MATCH.value:
                    return result
            
            # Step 7: Propose new table if no viable candidates
            return await self._propose_new_table_solution(operation_id, source_analysis, user_context)
            
        except Exception as e:
            logger.error(f"Error in column mapping workflow: {str(e)}")
            self._log_operation("ERROR", f"Workflow error: {str(e)}")
            return self._build_error_result(operation_id, f"Workflow error: {str(e)}")
    
    async def _check_existing_mapping(self, table: str, column: str) -> Dict[str, Any]:
        """Check if mapping already exists for the target table and column"""
        try:
            if not self.mcp_client or not self.mcp_client.session:
                return {"status": "error", "message": "MCP client not available"}
            
            result = await self.mcp_client.session.call_tool("get_column_mapping", {
                "table": table,
                "column": column
            })
            
            result_text = self._extract_tool_result(result)
            return json.loads(result_text)
            
        except Exception as e:
            logger.error(f"Error checking existing mapping: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _analyze_source_column(self, table: str, column: str) -> Dict[str, Any]:
        """Analyze the source column to get its full metadata profile"""
        try:
            if not self.mcp_client or not self.mcp_client.session:
                return {"status": "error", "message": "MCP client not available"}
            
            self._log_operation("ANALYZE_SOURCE", f"Analyzing source column {table}.{column}")
            
            result = await self.mcp_client.session.call_tool("analyze_unmapped_column", {
                "table": table,
                "column": column
            })
            
            result_text = self._extract_tool_result(result)
            return json.loads(result_text)
            
        except Exception as e:
            logger.error(f"Error analyzing source column: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _find_candidate_tables(self, subject_area: str) -> Dict[str, Any]:
        """Find candidate tables by subject area"""
        try:
            if not self.mcp_client or not self.mcp_client.session:
                return {"status": "error", "message": "MCP client not available"}
            
            self._log_operation("FIND_CANDIDATES", f"Finding candidates in {subject_area} subject area")
            
            result = await self.mcp_client.session.call_tool("find_candidate_tables_by_subject_area", {
                "subject_area": subject_area
            })
            
            result_text = self._extract_tool_result(result)
            return json.loads(result_text)
            
        except Exception as e:
            logger.error(f"Error finding candidate tables: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _analyze_candidates_granularity(self, source_table: str, 
                                            candidate_tables: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Analyze granularity fit for all candidate tables"""
        direct_fit = []
        needs_aggregation = []
        mismatch = []
        
        for candidate in candidate_tables:
            try:
                if not self.mcp_client or not self.mcp_client.session:
                    continue
                    
                result = await self.mcp_client.session.call_tool("analyze_granularity_fit", {
                    "source_table": source_table,
                    "target_table": candidate["table_name"]
                })
                
                result_text = self._extract_tool_result(result)
                analysis = json.loads(result_text)
                fit_status = analysis.get("fit_status", "MISMATCH")
                
                candidate_with_fit = candidate.copy()
                candidate_with_fit["granularity_analysis"] = analysis
                
                if fit_status == "DIRECT_FIT":
                    direct_fit.append(candidate_with_fit)
                elif fit_status == "REQUIRES_AGGREGATION":
                    needs_aggregation.append(candidate_with_fit)
                else:
                    mismatch.append(candidate_with_fit)
                    
            except Exception as e:
                logger.warning(f"Error analyzing granularity for {candidate.get('table_name')}: {str(e)}")
                mismatch.append(candidate)
        
        self._log_operation("GRANULARITY_ANALYSIS", 
                          f"Direct fit: {len(direct_fit)}, Aggregation: {len(needs_aggregation)}, Mismatch: {len(mismatch)}")
        
        return direct_fit, needs_aggregation, mismatch
    
    async def _process_direct_fit_candidates(self, operation_id: str, source_analysis: Dict, 
                                           candidates: List[Dict], target_table: str = None,
                                           target_column: str = None) -> Dict[str, Any]:
        """Process candidates that have direct granularity fit"""
        
        self._log_operation("PROCESS_DIRECT_FIT", f"Processing {len(candidates)} direct fit candidates")
        
        # If target table is specified, prioritize it
        if target_table:
            candidates = [c for c in candidates if c["table_name"].upper() == target_table.upper()] + \
                        [c for c in candidates if c["table_name"].upper() != target_table.upper()]
        
        for candidate in candidates:
            try:
                # Find semantic column matches
                column_matches = await self._find_semantic_matches(source_analysis, candidate["table_name"])
                
                if column_matches.get("match_count", 0) > 0:
                    best_match = column_matches["matches"][0]
                    
                    # If target column specified, check if it's in the matches
                    if target_column:
                        target_match = next(
                            (m for m in column_matches["matches"] 
                             if m["column_name"].upper() == target_column.upper()), 
                            None
                        )
                        if target_match:
                            best_match = target_match
                    
                    # Only proceed with high confidence matches for direct fit
                    if best_match["confidence_score"] >= 0.7:
                        # Find join path
                        join_path = await self._find_join_path(
                            source_analysis["column_profile"]["table_name"],
                            candidate["table_name"]
                        )
                        
                        if join_path.get("path_found"):
                            # Generate ETL logic
                            mapping_result = await self._generate_mapping_logic(
                                source_analysis, best_match, candidate, join_path
                            )
                            
                            if mapping_result.get("status") == "generated":
                                self._log_operation("SUCCESS", 
                                                  f"Direct mapping found: {candidate['table_name']}.{best_match['column_name']}")
                                return {
                                    "operation_id": operation_id,
                                    "status": MappingStatus.SUCCESS.value,
                                    "result_type": "direct_mapping",
                                    "target_table": candidate["table_name"],
                                    "target_column": best_match["column_name"],
                                    "confidence_score": best_match["confidence_score"],
                                    "mapping_logic": mapping_result,
                                    "join_path": join_path,
                                    "granularity_analysis": candidate.get("granularity_analysis"),
                                    "operations_log": self.operation_log
                                }
                        else:
                            self._log_operation("NO_JOIN_PATH", 
                                              f"No join path found to {candidate['table_name']}")
            
            except Exception as e:
                logger.warning(f"Error processing candidate {candidate.get('table_name')}: {str(e)}")
                continue
        
        self._log_operation("NO_DIRECT_MATCH", "No viable direct fit mappings found")
        return {
            "operation_id": operation_id,
            "status": MappingStatus.FAILED_NO_MATCH.value,
            "message": "No high-confidence direct mappings found"
        }
    
    async def _process_aggregation_candidates(self, operation_id: str, source_analysis: Dict,
                                            candidates: List[Dict], target_table: str = None,
                                            target_column: str = None) -> Dict[str, Any]:
        """Process candidates that require aggregation"""
        
        self._log_operation("PROCESS_AGGREGATION", f"Processing {len(candidates)} aggregation candidates")
        
        # Similar to direct fit but with aggregation context
        for candidate in candidates:
            try:
                column_matches = await self._find_semantic_matches(source_analysis, candidate["table_name"])
                
                if column_matches.get("match_count", 0) > 0:
                    best_match = column_matches["matches"][0]
                    
                    if target_column:
                        target_match = next(
                            (m for m in column_matches["matches"] 
                             if m["column_name"].upper() == target_column.upper()),
                            None
                        )
                        if target_match:
                            best_match = target_match
                    
                    # Lower threshold for aggregation candidates
                    if best_match["confidence_score"] >= 0.6:
                        join_path = await self._find_join_path(
                            source_analysis["column_profile"]["table_name"],
                            candidate["table_name"]
                        )
                        
                        if join_path.get("path_found"):
                            # Generate ETL logic with aggregation context
                            mapping_result = await self._generate_mapping_logic(
                                source_analysis, best_match, candidate, join_path, requires_aggregation=True
                            )
                            
                            if mapping_result.get("status") == "generated":
                                self._log_operation("SUCCESS_AGGREGATION", 
                                                  f"Aggregation mapping found: {candidate['table_name']}.{best_match['column_name']}")
                                return {
                                    "operation_id": operation_id,
                                    "status": MappingStatus.SUCCESS_WITH_AGGREGATION.value,
                                    "result_type": "aggregation_mapping",
                                    "target_table": candidate["table_name"],
                                    "target_column": best_match["column_name"],
                                    "confidence_score": best_match["confidence_score"],
                                    "mapping_logic": mapping_result,
                                    "join_path": join_path,
                                    "granularity_analysis": candidate.get("granularity_analysis"),
                                    "requires_user_consent": True,
                                    "warning": "This mapping requires aggregation, which changes data granularity",
                                    "operations_log": self.operation_log
                                }
            
            except Exception as e:
                logger.warning(f"Error processing aggregation candidate {candidate.get('table_name')}: {str(e)}")
                continue
        
        return {
            "operation_id": operation_id,
            "status": MappingStatus.FAILED_NO_MATCH.value,
            "message": "No viable aggregation mappings found"
        }
    
    async def _find_semantic_matches(self, source_analysis: Dict, target_table: str) -> Dict[str, Any]:
        """Find semantic column matches in target table"""
        try:
            if not self.mcp_client or not self.mcp_client.session:
                return {"status": "error", "message": "MCP client not available"}
            
            source_column_info = json.dumps(source_analysis.get("column_profile", {}))
            
            result = await self.mcp_client.session.call_tool("find_semantic_column_matches", {
                "source_column_info": source_column_info,
                "target_table": target_table
            })
            
            result_text = self._extract_tool_result(result)
            return json.loads(result_text)
            
        except Exception as e:
            logger.error(f"Error finding semantic matches: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _find_join_path(self, start_table: str, end_table: str) -> Dict[str, Any]:
        """Find join path between tables"""
        try:
            if not self.mcp_client or not self.mcp_client.session:
                return {"status": "error", "message": "MCP client not available"}
            
            result = await self.mcp_client.session.call_tool("find_join_path", {
                "start_table": start_table,
                "end_table": end_table
            })
            
            result_text = self._extract_tool_result(result)
            return json.loads(result_text)
            
        except Exception as e:
            logger.error(f"Error finding join path: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _generate_mapping_logic(self, source_analysis: Dict, target_match: Dict, 
                                    target_table: Dict, join_path: Dict,
                                    requires_aggregation: bool = False) -> Dict[str, Any]:
        """Generate ETL mapping logic"""
        try:
            if not self.mcp_client or not self.mcp_client.session:
                return {"status": "error", "message": "MCP client not available"}
            
            # Prepare source and target info for ETL generation
            source_info = {
                "column_name": source_analysis["column_profile"]["column_name"],
                "table_name": source_analysis["column_profile"]["table_name"],
                "data_type": source_analysis["column_profile"]["data_type"],
                "business_name": source_analysis["column_profile"]["business_name"],
                "description": source_analysis["column_profile"]["description"],
                "tags": source_analysis["column_profile"]["tags"],
                "subject_area": source_analysis["table_context"]["subject_area"]
            }
            
            target_info = {
                "column_name": target_match["column_name"],
                "table_name": target_table["table_name"],
                "data_type": target_match["data_type"],
                "business_name": target_match["business_name"],
                "description": target_match["description"],
                "tags": target_match["tags"],
                "requires_aggregation": requires_aggregation
            }
            
            join_clause = join_path.get("full_from_clause", "")
            
            result = await self.mcp_client.session.call_tool("generate_etl_logic", {
                "source_info": json.dumps(source_info),
                "target_info": json.dumps(target_info),
                "join_clause": join_clause
            })
            
            result_text = self._extract_tool_result(result)
            return json.loads(result_text)
            
        except Exception as e:
            logger.error(f"Error generating mapping logic: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _propose_new_table_solution(self, operation_id: str, source_analysis: Dict,
                                        user_context: str = "") -> Dict[str, Any]:
        """Propose new table structure when no viable candidates exist"""
        try:
            if not self.mcp_client or not self.mcp_client.session:
                return self._build_error_result(operation_id, "MCP client not available")
            
            self._log_operation("PROPOSE_TABLE", "Proposing new table structure")
            
            subject_area = source_analysis.get("table_context", {}).get("subject_area", "General")
            granularity = source_analysis.get("table_context", {}).get("granularity", "Unknown")
            
            # Extract column requirements from source analysis and context
            required_columns = [source_analysis["column_profile"]["column_name"]]
            if user_context:
                required_columns.append(f"Context: {user_context}")
            
            result = await self.mcp_client.session.call_tool("propose_new_table_structure", {
                "subject_area": subject_area,
                "required_columns": json.dumps(required_columns),
                "required_granularity": granularity
            })
            
            result_text = self._extract_tool_result(result)
            table_proposal = json.loads(result_text)
            
            self._log_operation("TABLE_PROPOSED", f"New table proposed: {table_proposal.get('table_name')}")
            
            return {
                "operation_id": operation_id,
                "status": MappingStatus.REQUIRES_NEW_TABLE.value,
                "result_type": "new_table_proposal",
                "table_proposal": table_proposal,
                "source_analysis": source_analysis,
                "recommendation": "No existing tables can accommodate this mapping. A new table is recommended.",
                "operations_log": self.operation_log
            }
            
        except Exception as e:
            logger.error(f"Error proposing new table: {str(e)}")
            return self._build_error_result(operation_id, f"Failed to propose new table: {str(e)}")
    
    def _log_operation(self, operation_type: str, description: str):
        """Log an operation step"""
        self.operation_log.append({
            "timestamp": datetime.now().isoformat(),
            "operation": operation_type,
            "description": description
        })
        logger.info(f"[{operation_type}] {description}")
    
    def _build_error_result(self, operation_id: str, message: str, details: Dict = None) -> Dict[str, Any]:
        """Build standardized error result"""
        return {
            "operation_id": operation_id,
            "status": MappingStatus.ERROR.value,
            "error_message": message,
            "error_details": details,
            "operations_log": self.operation_log
        }
    
    async def get_catalog_overview(self) -> Dict[str, Any]:
        """Get overview of the data catalog"""
        try:
            if not self.mcp_client or not self.mcp_client.session:
                return {"status": "error", "message": "MCP client not available"}
            
            result = await self.mcp_client.session.call_tool("get_catalog_overview", {})
            result_text = self._extract_tool_result(result)
            return json.loads(result_text)
            
        except Exception as e:
            logger.error(f"Error getting catalog overview: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def bulk_analyze_columns(self, column_list: List[Tuple[str, str]]) -> Dict[str, Any]:
        """
        Analyze multiple columns in batch for mapping opportunities
        
        Args:
            column_list: List of (table, column) tuples to analyze
            
        Returns:
            Dictionary with bulk analysis results
        """
        results = {}
        operation_id = str(uuid.uuid4())
        
        logger.info(f"Starting bulk analysis of {len(column_list)} columns")
        
        for table, column in column_list:
            try:
                result = await self.map_column(table, column)
                results[f"{table}.{column}"] = result
            except Exception as e:
                logger.error(f"Error analyzing {table}.{column}: {str(e)}")
                results[f"{table}.{column}"] = {
                    "status": MappingStatus.ERROR.value,
                    "error_message": str(e)
                }
        
        # Summarize results
        status_summary = {}
        for result in results.values():
            status = result.get("status", "unknown")
            status_summary[status] = status_summary.get(status, 0) + 1
        
        return {
            "operation_id": operation_id,
            "total_columns": len(column_list),
            "status_summary": status_summary,
            "detailed_results": results,
            "completion_timestamp": datetime.now().isoformat()
        }
