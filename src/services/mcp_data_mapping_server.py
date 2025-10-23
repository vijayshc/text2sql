"""
MCP Data Mapping Analyst Server - HTTP/SSE implementation
Provides Model Context Protocol interface for AI Data Mapping functionality

This server implements the AI Data Mapping Analyst Agent that replicates 
the workflow of an expert data architect. It intelligently analyzes, maps, 
and models data for enterprise data warehouses and data marts.
"""

import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional
import networkx as nx
from datetime import datetime

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route

from src.utils.data_catalog_utils import (
    load_data_catalog, load_data_mappings, get_table_by_name, 
    get_column_by_name, get_tables_by_subject_area, get_column_mapping,
    get_relationships_for_table, save_mapping, get_all_subject_areas,
    get_catalog_stats, get_columns_with_tags
)
from src.utils.common_llm import get_llm_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('mcp_data_mapping_server')

# Initialize FastMCP server for Data Mapping tools (SSE)
mcp = FastMCP("data-mapping-analyst")


@mcp.tool()
async def get_column_mapping(table: str, column: str) -> str:
    """Get existing mapping for a table and column.
    
    Args:
        table: Target table name
        column: Target column name
        
    Returns:
        JSON string of the mapping object if found, otherwise status not_found
    """
    try:
        if not table or not column:
            return json.dumps({"status": "error", "message": "Table and column parameters are required"})
        
        mapping = get_column_mapping(table, column)
        
        if mapping:
            return json.dumps({
                "status": "found",
                "mapping": mapping
            })
        else:
            return json.dumps({
                "status": "not_found",
                "message": f"No active mapping found for {table}.{column}"
            })
            
    except Exception as e:
        logger.error(f"Error getting column mapping: {str(e)}")
        return json.dumps({
            "status": "error", 
            "message": f"Failed to get column mapping: {str(e)}"
        })


@mcp.tool()
async def analyze_unmapped_column(table: str, column: str) -> str:
    """Analyze an unmapped column to get its full metadata profile.
    
    Args:
        table: Table name containing the column
        column: Column name to analyze
        
    Returns:
        JSON string containing the column's full metadata profile
    """
    try:
        if not table or not column:
            return json.dumps({"status": "error", "message": "Table and column parameters are required"})
        
        # Get column information from catalog
        column_info = get_column_by_name(table, column)
        
        if not column_info:
            return json.dumps({
                "status": "not_found",
                "message": f"Column {column} not found in table {table}"
            })
        
        # Get table information for context
        table_info = get_table_by_name(table)
        
        if not table_info:
            return json.dumps({
                "status": "error",
                "message": f"Table {table} not found in catalog"
            })
        
        # Enhance description using LLM if it's sparse
        enhanced_description = column_info['description']
        if len(column_info['description']) < 50:
            try:
                llm = get_llm_engine()
                
                enhancement_prompt = f"""
                Analyze this database column and provide a detailed business description:
                
                Column: {column_info['columnName']}
                Table: {table_info['tableName']} ({table_info['businessName']})
                Current Description: {column_info['description']}
                Data Type: {column_info['dataType']}
                Tags: {', '.join(column_info.get('tags', []))}
                Subject Area: {table_info['subjectArea']}
                Table Type: {table_info['tableType']}
                Table Granularity: {table_info['granularity']}
                
                Provide a comprehensive business description (2-3 sentences) that explains:
                1. What this column represents in business terms
                2. How it's typically used in {table_info['subjectArea']} analysis
                3. Any business rules or constraints that might apply
                
                Return only the enhanced description text, no additional formatting.
                """
                
                enhanced_description = llm.complete(enhancement_prompt)
                
            except Exception as llm_error:
                logger.warning(f"LLM enhancement failed: {str(llm_error)}")
                # Continue with original description
        
        # Build comprehensive profile
        profile = {
            "status": "analyzed",
            "column_profile": {
                "column_name": column_info['columnName'],
                "table_name": table_info['tableName'],
                "schema_name": column_info.get('schemaName'),
                "data_type": column_info['dataType'],
                "business_name": column_info['businessName'],
                "description": enhanced_description,
                "is_nullable": column_info['isNullable'],
                "is_natural_key": column_info['isNaturalKey'],
                "is_pii": column_info['isPII'],
                "security_classification": column_info['securityClassification'],
                "tags": column_info.get('tags', []),
                "valid_value_ranges": column_info['validValueRanges']
            },
            "table_context": {
                "table_type": table_info['tableType'],
                "business_name": table_info['businessName'],
                "subject_area": table_info['subjectArea'],
                "granularity": table_info['granularity'],
                "primary_key": table_info['primaryKey'],
                "update_frequency": table_info['updateFrequency']
            }
        }
        
        return json.dumps(profile, indent=2)
        
    except Exception as e:
        logger.error(f"Error analyzing unmapped column: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to analyze column: {str(e)}"
        })


@mcp.tool()
async def find_candidate_tables_by_subject_area(subject_area: str) -> str:
    """Find candidate tables for mapping based on subject area.
    
    Args:
        subject_area: Subject area to search for tables
        
    Returns:
        JSON string of tables with their metadata
    """
    try:
        if not subject_area:
            return json.dumps({"status": "error", "message": "Subject area parameter is required"})
        
        tables = get_tables_by_subject_area(subject_area)
        
        if not tables:
            return json.dumps({
                "status": "no_results",
                "message": f"No tables found for subject area: {subject_area}",
                "available_subject_areas": get_all_subject_areas()
            })
        
        # Format tables for response
        candidate_tables = []
        for table in tables:
            candidate_tables.append({
                "table_name": table['tableName'],
                "schema_name": table.get('schemaName'),
                "business_name": table['businessName'],
                "table_type": table['tableType'],
                "granularity": table['granularity'],
                "primary_key": table['primaryKey'],
                "column_count": len(table.get('columns', [])),
                "update_frequency": table['updateFrequency']
            })
        
        return json.dumps({
            "status": "found",
            "subject_area": subject_area,
            "table_count": len(candidate_tables),
            "tables": candidate_tables
        }, indent=2)
        
    except Exception as e:
        logger.error(f"Error finding candidate tables: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to find candidate tables: {str(e)}"
        })


@mcp.tool()
async def analyze_granularity_fit(source_table: str, target_table: str) -> str:
    """Analyze if source and target tables have compatible granularity.
    
    Args:
        source_table: Name of the source table
        target_table: Name of the target table
        
    Returns:
        JSON string with granularity fit analysis
    """
    try:
        if not source_table or not target_table:
            return json.dumps({"status": "error", "message": "Source and target table parameters are required"})
        
        # Get table information
        source_info = get_table_by_name(source_table)
        target_info = get_table_by_name(target_table)
        
        if not source_info:
            return json.dumps({"status": "error", "message": f"Source table {source_table} not found"})
        
        if not target_info:
            return json.dumps({"status": "error", "message": f"Target table {target_table} not found"})
        
        # Use LLM to analyze granularity compatibility
        try:
            llm = get_llm_engine()
            
            granularity_prompt = f"""
            Analyze the granularity compatibility between these two database tables:
            
            SOURCE TABLE: {source_info['tableName']}
            - Business Name: {source_info['businessName']}
            - Granularity: {source_info['granularity']}
            - Primary Key: {', '.join(source_info['primaryKey'])}
            - Table Type: {source_info['tableType']}
            
            TARGET TABLE: {target_info['tableName']}
            - Business Name: {target_info['businessName']}
            - Granularity: {target_info['granularity']}
            - Primary Key: {', '.join(target_info['primaryKey'])}
            - Table Type: {target_info['tableType']}
            
            Determine the granularity fit and respond with EXACTLY one of these values:
            - DIRECT_FIT: Tables have identical or compatible granularity for direct mapping
            - REQUIRES_AGGREGATION: Source is more detailed, needs aggregation to match target
            - MISMATCH: Tables have incompatible granularity that cannot be easily reconciled
            
            After the fit status, provide a 2-3 sentence justification explaining your reasoning.
            
            Format your response as:
            FIT_STATUS: [status]
            JUSTIFICATION: [explanation]
            """
            
            response = llm.complete(granularity_prompt)
            
            # Parse LLM response
            lines = response.strip().split('\n')
            fit_status = "MISMATCH"  # Default
            justification = "Unable to determine granularity fit"
            
            for line in lines:
                if line.startswith("FIT_STATUS:"):
                    fit_status = line.split(":", 1)[1].strip()
                elif line.startswith("JUSTIFICATION:"):
                    justification = line.split(":", 1)[1].strip()
            
            # Validate fit status
            valid_statuses = ["DIRECT_FIT", "REQUIRES_AGGREGATION", "MISMATCH"]
            if fit_status not in valid_statuses:
                fit_status = "MISMATCH"
                justification = f"Invalid analysis result. {justification}"
            
        except Exception as llm_error:
            logger.warning(f"LLM granularity analysis failed: {str(llm_error)}")
            # Fallback to simple comparison
            if source_info['granularity'].lower() == target_info['granularity'].lower():
                fit_status = "DIRECT_FIT"
                justification = "Tables have identical granularity descriptions"
            else:
                fit_status = "MISMATCH"
                justification = "Tables have different granularity descriptions"
        
        result = {
            "status": "analyzed",
            "source_table": source_table,
            "target_table": target_table,
            "fit_status": fit_status,
            "justification": justification,
            "source_granularity": source_info['granularity'],
            "target_granularity": target_info['granularity'],
            "source_primary_key": source_info['primaryKey'],
            "target_primary_key": target_info['primaryKey']
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error analyzing granularity fit: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to analyze granularity fit: {str(e)}"
        })


@mcp.tool()
async def find_join_path(start_table: str, end_table: str) -> str:
    """Find the join path between two tables using relationship metadata.
    
    Args:
        start_table: Starting table name
        end_table: Target table name
        
    Returns:
        JSON string with join path information
    """
    try:
        if not start_table or not end_table:
            return json.dumps({"status": "error", "message": "Start and end table parameters are required"})
        
        # Build graph from catalog relationships
        catalog = load_data_catalog()
        G = nx.DiGraph()
        
        # Add all tables as nodes and relationships as edges
        for schema in catalog.get('schemas', []):
            for table in schema.get('tables', []):
                table_name = table['tableName']
                G.add_node(table_name, **table)
                
                # Add relationships as directed edges
                for rel in table.get('relationships', []):
                    to_table = rel['toTable']
                    G.add_edge(table_name, to_table, **rel)
        
        # Find shortest path
        try:
            if start_table not in G.nodes():
                return json.dumps({
                    "status": "error",
                    "message": f"Start table {start_table} not found in catalog"
                })
            
            if end_table not in G.nodes():
                return json.dumps({
                    "status": "error", 
                    "message": f"End table {end_table} not found in catalog"
                })
            
            # Try to find path in both directions
            path = None
            try:
                path = nx.shortest_path(G, start_table, end_table)
            except nx.NetworkXNoPath:
                # Try reverse direction
                try:
                    reverse_path = nx.shortest_path(G, end_table, start_table)
                    path = list(reversed(reverse_path))
                except nx.NetworkXNoPath:
                    pass
            
            if not path:
                return json.dumps({
                    "path_found": False,
                    "message": f"No join path found between {start_table} and {end_table}",
                    "steps": [],
                    "full_from_clause": ""
                })
            
            # Build join steps and FROM clause
            steps = []
            from_clause_parts = [path[0]]
            
            for i in range(len(path) - 1):
                current_table = path[i]
                next_table = path[i + 1]
                
                # Find the relationship details
                edge_data = G.get_edge_data(current_table, next_table)
                if not edge_data:
                    # Try reverse edge
                    edge_data = G.get_edge_data(next_table, current_table)
                
                if edge_data:
                    join_conditions = edge_data.get('joinConditions', [])
                    join_type = edge_data.get('type', 'LINK')
                    bridge_table = edge_data.get('bridgeTable')
                    
                    if bridge_table:
                        # Handle bridge table (many-to-many)
                        steps.append({
                            "from_table": current_table,
                            "to_table": bridge_table,
                            "join_type": "INNER JOIN",
                            "relationship_type": join_type
                        })
                        steps.append({
                            "from_table": bridge_table,
                            "to_table": next_table,
                            "join_type": "INNER JOIN",
                            "relationship_type": join_type
                        })
                        from_clause_parts.extend([
                            f"INNER JOIN {bridge_table} ON {current_table}.{join_conditions[0]['fromColumn']} = {bridge_table}.{join_conditions[0]['toColumn']}",
                            f"INNER JOIN {next_table} ON {bridge_table}.{join_conditions[0]['fromColumn']} = {next_table}.{join_conditions[0]['toColumn']}"
                        ])
                    else:
                        # Direct join
                        join_clause = " AND ".join([
                            f"{current_table}.{jc['fromColumn']} = {next_table}.{jc['toColumn']}"
                            for jc in join_conditions
                        ])
                        
                        join_type_sql = "LEFT JOIN" if join_type == "LOOKUP" else "INNER JOIN"
                        
                        steps.append({
                            "from_table": current_table,
                            "to_table": next_table,
                            "join_type": join_type_sql,
                            "join_condition": join_clause,
                            "relationship_type": join_type
                        })
                        
                        from_clause_parts.append(f"{join_type_sql} {next_table} ON {join_clause}")
                else:
                    # No explicit relationship found, use table names as fallback
                    steps.append({
                        "from_table": current_table,
                        "to_table": next_table,
                        "join_type": "INNER JOIN",
                        "join_condition": f"-- Join condition needed for {current_table} to {next_table}",
                        "relationship_type": "INFERRED"
                    })
                    from_clause_parts.append(f"INNER JOIN {next_table} ON -- condition needed")
            
            full_from_clause = "\n  ".join(from_clause_parts)
            
            result = {
                "path_found": True,
                "start_table": start_table,
                "end_table": end_table,
                "path_length": len(path),
                "steps": steps,
                "table_sequence": path,
                "full_from_clause": f"FROM {full_from_clause}"
            }
            
            return json.dumps(result, indent=2)
            
        except Exception as path_error:
            logger.error(f"Error finding path: {str(path_error)}")
            return json.dumps({
                "path_found": False,
                "message": f"Error finding path: {str(path_error)}",
                "steps": [],
                "full_from_clause": ""
            })
            
    except Exception as e:
        logger.error(f"Error in find_join_path: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to find join path: {str(e)}"
        })


@mcp.tool()
async def find_semantic_column_matches(source_column_info: str, target_table: str) -> str:
    """Find semantically similar columns in the target table.
    
    Args:
        source_column_info: JSON string with source column profile
        target_table: Name of the target table to search in
        
    Returns:
        JSON string with ranked list of potential target columns
    """
    try:
        if not source_column_info or not target_table:
            return json.dumps({"status": "error", "message": "Source column info and target table parameters are required"})
        
        # Parse source column info
        try:
            source_info = json.loads(source_column_info)
        except json.JSONDecodeError:
            return json.dumps({"status": "error", "message": "Invalid JSON in source_column_info parameter"})
        
        # Get target table information
        target_table_info = get_table_by_name(target_table)
        
        if not target_table_info:
            return json.dumps({
                "status": "error",
                "message": f"Target table {target_table} not found in catalog"
            })
        
        # Use LLM to find semantic matches
        try:
            llm = get_llm_engine()
            
            # Build target columns description
            target_columns_desc = []
            for col in target_table_info.get('columns', []):
                col_desc = f"""
                Column: {col['columnName']}
                Business Name: {col['businessName']}
                Data Type: {col['dataType']}
                Description: {col['description']}
                Tags: {', '.join(col.get('tags', []))}
                Is Natural Key: {col.get('isNaturalKey', False)}
                Is PII: {col.get('isPII', False)}
                """
                target_columns_desc.append(col_desc.strip())
            
            semantic_prompt = f"""
            Find the most semantically similar columns in the target table for the given source column.
            
            SOURCE COLUMN:
            Column: {source_info.get('column_name', 'Unknown')}
            Business Name: {source_info.get('business_name', 'Unknown')}
            Data Type: {source_info.get('data_type', 'Unknown')}
            Description: {source_info.get('description', 'Unknown')}
            Tags: {', '.join(source_info.get('tags', []))}
            Subject Area: {source_info.get('subject_area', 'Unknown')}
            
            TARGET TABLE: {target_table}
            TARGET COLUMNS:
            {chr(10).join(target_columns_desc)}
            
            Rank the target columns by semantic similarity to the source column. Consider:
            1. Business meaning and purpose
            2. Data type compatibility
            3. Naming conventions
            4. Tag similarity
            5. Functional role (keys, measures, attributes)
            
            Return a JSON list of matches, ordered by confidence (highest first):
            [
              {{
                "column_name": "column_name",
                "confidence_score": 0.95,
                "match_reason": "explanation of why this is a good match"
              }}
            ]
            
            Only include columns with confidence > 0.3. Provide realistic confidence scores between 0.0 and 1.0.
            Return only the JSON array, no additional text.
            """
            
            response = llm.complete(semantic_prompt)
            
            # Parse LLM response
            try:
                matches = json.loads(response.strip())
                
                # Validate and enhance matches with full column info
                enhanced_matches = []
                for match in matches:
                    if isinstance(match, dict) and 'column_name' in match:
                        # Find full column info
                        full_col_info = get_column_by_name(target_table, match['column_name'])
                        if full_col_info:
                            enhanced_match = {
                                "column_name": match['column_name'],
                                "confidence_score": match.get('confidence_score', 0.5),
                                "match_reason": match.get('match_reason', 'Semantic similarity detected'),
                                "business_name": full_col_info['businessName'],
                                "data_type": full_col_info['dataType'],
                                "description": full_col_info['description'],
                                "tags": full_col_info.get('tags', []),
                                "is_natural_key": full_col_info.get('isNaturalKey', False),
                                "is_pii": full_col_info.get('isPII', False)
                            }
                            enhanced_matches.append(enhanced_match)
                
                result = {
                    "status": "analyzed",
                    "source_column": source_info.get('column_name', 'Unknown'),
                    "target_table": target_table,
                    "match_count": len(enhanced_matches),
                    "matches": enhanced_matches
                }
                
                return json.dumps(result, indent=2)
                
            except json.JSONDecodeError:
                # Fallback to simple string-based matching
                logger.warning("LLM returned invalid JSON, using fallback matching")
                
        except Exception as llm_error:
            logger.warning(f"LLM semantic matching failed: {str(llm_error)}")
        
        # Fallback: Simple tag and name-based matching
        source_tags = set(tag.lower() for tag in source_info.get('tags', []))
        source_name_parts = set(source_info.get('column_name', '').lower().split('_'))
        
        fallback_matches = []
        for col in target_table_info.get('columns', []):
            col_tags = set(tag.lower() for tag in col.get('tags', []))
            col_name_parts = set(col['columnName'].lower().split('_'))
            
            # Calculate simple similarity
            tag_overlap = len(source_tags.intersection(col_tags))
            name_overlap = len(source_name_parts.intersection(col_name_parts))
            
            if tag_overlap > 0 or name_overlap > 0:
                confidence = (tag_overlap * 0.6 + name_overlap * 0.4) / max(len(source_tags) + len(source_name_parts), 1)
                confidence = min(confidence, 0.8)  # Cap fallback confidence
                
                if confidence > 0.3:
                    fallback_matches.append({
                        "column_name": col['columnName'],
                        "confidence_score": round(confidence, 2),
                        "match_reason": f"Tag overlap: {tag_overlap}, Name overlap: {name_overlap}",
                        "business_name": col['businessName'],
                        "data_type": col['dataType'],
                        "description": col['description'],
                        "tags": col.get('tags', []),
                        "is_natural_key": col.get('isNaturalKey', False),
                        "is_pii": col.get('isPII', False)
                    })
        
        # Sort by confidence
        fallback_matches.sort(key=lambda x: x['confidence_score'], reverse=True)
        
        result = {
            "status": "analyzed",
            "source_column": source_info.get('column_name', 'Unknown'),
            "target_table": target_table,
            "match_count": len(fallback_matches),
            "matches": fallback_matches,
            "note": "Fallback matching used due to LLM analysis failure"
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error finding semantic column matches: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to find semantic column matches: {str(e)}"
        })


@mcp.tool()
async def generate_etl_logic(source_info: str, target_info: str, join_clause: str) -> str:
    """Generate ETL transformation logic for mapping source to target column.
    
    Args:
        source_info: JSON string with source column/table information
        target_info: JSON string with target column/table information  
        join_clause: Full FROM clause with joins needed to access source data
        
    Returns:
        JSON string with transformation expression and business rule
    """
    try:
        if not source_info or not target_info:
            return json.dumps({"status": "error", "message": "Source and target info parameters are required"})
        
        # Parse input parameters
        try:
            source_data = json.loads(source_info)
            target_data = json.loads(target_info)
        except json.JSONDecodeError as e:
            return json.dumps({"status": "error", "message": f"Invalid JSON in parameters: {str(e)}"})
        
        # Use LLM to generate transformation logic
        try:
            llm = get_llm_engine()
            
            etl_prompt = f"""
            Generate SQL transformation logic to map source data to target column.
            
            SOURCE INFORMATION:
            {json.dumps(source_data, indent=2)}
            
            TARGET INFORMATION:
            {json.dumps(target_data, indent=2)}
            
            JOIN CLAUSE (if provided):
            {join_clause if join_clause else "No join clause provided"}
            
            Generate ONLY the SELECT expression for the target column, considering:
            1. Data type conversions if needed
            2. Business rules and transformations
            3. Data quality and standardization
            4. Null handling
            5. Aggregation if granularity differs
            
            Return a JSON object with:
            {{
              "expression": "SQL SELECT expression for the target column",
              "business_rule": "Plain English explanation of the transformation",
              "data_quality_notes": "Any data quality considerations",
              "requires_aggregation": true/false
            }}
            
            Example expressions:
            - Simple mapping: "source_table.source_column"
            - With transformation: "UPPER(TRIM(source_table.customer_name))"
            - With calculation: "source_table.quantity * source_table.unit_price"
            - With lookup: "dim_table.surrogate_key"
            - With aggregation: "SUM(source_table.amount)"
            
            Return only the JSON object, no additional text.
            """
            
            response = llm.complete(etl_prompt)
            
            # Parse LLM response
            try:
                etl_result = json.loads(response.strip())
                
                # Validate required fields
                if not isinstance(etl_result, dict) or 'expression' not in etl_result:
                    raise ValueError("Invalid ETL result format")
                
                # Enhance with metadata
                enhanced_result = {
                    "status": "generated",
                    "source_column": source_data.get('column_name', 'Unknown'),
                    "target_column": target_data.get('column_name', 'Unknown'),
                    "expression": etl_result.get('expression', ''),
                    "business_rule": etl_result.get('business_rule', 'Direct mapping'),
                    "data_quality_notes": etl_result.get('data_quality_notes', ''),
                    "requires_aggregation": etl_result.get('requires_aggregation', False),
                    "generated_at": datetime.now().isoformat()
                }
                
                return json.dumps(enhanced_result, indent=2)
                
            except (json.JSONDecodeError, ValueError) as parse_error:
                logger.warning(f"LLM returned invalid JSON: {str(parse_error)}")
                
        except Exception as llm_error:
            logger.warning(f"LLM ETL generation failed: {str(llm_error)}")
        
        # Fallback: Generate simple mapping based on column types
        source_col = source_data.get('column_name', 'source_column')
        source_table = source_data.get('table_name', 'source_table')
        source_type = source_data.get('data_type', '').upper()
        target_type = target_data.get('data_type', '').upper()
        
        # Simple expression generation
        expression = f"{source_table}.{source_col}"
        business_rule = "Direct column mapping"
        requires_aggregation = False
        
        # Apply basic transformations based on data types
        if 'VARCHAR' in target_type and 'VARCHAR' not in source_type:
            expression = f"CAST({expression} AS VARCHAR)"
            business_rule = "Convert to string representation"
        elif 'NUMBER' in target_type and 'VARCHAR' in source_type:
            expression = f"CAST({expression} AS NUMBER)"
            business_rule = "Convert string to number"
        elif source_col.lower().endswith('_name') or 'name' in source_col.lower():
            expression = f"UPPER(TRIM({expression}))"
            business_rule = "Standardize name format (uppercase, trimmed)"
        
        fallback_result = {
            "status": "generated",
            "source_column": source_col,
            "target_column": target_data.get('column_name', 'Unknown'),
            "expression": expression,
            "business_rule": business_rule,
            "data_quality_notes": "Basic fallback transformation applied",
            "requires_aggregation": requires_aggregation,
            "generated_at": datetime.now().isoformat(),
            "note": "Fallback logic used due to LLM generation failure"
        }
        
        return json.dumps(fallback_result, indent=2)
        
    except Exception as e:
        logger.error(f"Error generating ETL logic: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to generate ETL logic: {str(e)}"
        })


@mcp.tool()
async def propose_new_table_structure(subject_area: str, required_columns: str, required_granularity: str) -> str:
    """Propose a new table structure for missing data modeling requirements.
    
    Args:
        subject_area: Subject area for the new table
        required_columns: JSON string with list of required business concepts/columns
        required_granularity: Description of required data granularity
        
    Returns:
        JSON string with DDL script and justification
    """
    try:
        if not subject_area or not required_columns or not required_granularity:
            return json.dumps({
                "status": "error", 
                "message": "Subject area, required columns, and granularity parameters are required"
            })
        
        # Parse required columns
        try:
            columns_list = json.loads(required_columns) if isinstance(required_columns, str) else required_columns
        except json.JSONDecodeError:
            # Treat as plain text list
            columns_list = [col.strip() for col in required_columns.split(',')]
        
        # Get existing tables in subject area for context
        existing_tables = get_tables_by_subject_area(subject_area)
        
        # Use LLM to generate table structure
        try:
            llm = get_llm_engine()
            
            existing_context = ""
            if existing_tables:
                existing_context = "EXISTING TABLES IN " + subject_area.upper() + ":\n"
                for table in existing_tables[:3]:  # Limit to first 3 for context
                    existing_context += f"- {table['tableName']}: {table['businessName']} ({table['tableType']})\n"
                    existing_context += f"  Granularity: {table['granularity']}\n"
                    existing_context += f"  Columns: {len(table.get('columns', []))}\n\n"
            
            structure_prompt = f"""
            Design a new database table structure for the {subject_area} subject area.
            
            REQUIREMENTS:
            - Subject Area: {subject_area}
            - Required Granularity: {required_granularity}
            - Required Columns/Concepts: {', '.join(columns_list) if isinstance(columns_list, list) else columns_list}
            
            {existing_context}
            
            Generate a complete DDL CREATE TABLE statement following these guidelines:
            1. Use appropriate data types for each column
            2. Include primary key definition
            3. Add appropriate constraints
            4. Follow naming conventions (uppercase table/column names)
            5. Include business-friendly column comments
            6. Consider the table type (FACT, DIMENSION, STAGING, etc.) based on granularity
            
            Return a JSON object with:
            {{
              "table_name": "proposed table name",
              "table_type": "FACT/DIMENSION/STAGING/etc",
              "ddl_script": "complete CREATE TABLE DDL",
              "justification": "explanation of design decisions",
              "recommended_relationships": ["list of tables this should relate to"],
              "data_model_impact": "description of how this fits in the overall model"
            }}
            
            Return only the JSON object, no additional text.
            """
            
            response = llm.complete(structure_prompt)
            
            # Parse LLM response
            try:
                table_design = json.loads(response.strip())
                
                # Validate required fields
                required_fields = ['table_name', 'ddl_script', 'justification']
                if not all(field in table_design for field in required_fields):
                    raise ValueError("Missing required fields in table design")
                
                # Enhance with metadata
                enhanced_design = {
                    "status": "proposed",
                    "subject_area": subject_area,
                    "required_granularity": required_granularity,
                    "required_columns": columns_list,
                    "table_name": table_design.get('table_name', ''),
                    "table_type": table_design.get('table_type', 'STAGING'),
                    "ddl_script": table_design.get('ddl_script', ''),
                    "justification": table_design.get('justification', ''),
                    "recommended_relationships": table_design.get('recommended_relationships', []),
                    "data_model_impact": table_design.get('data_model_impact', ''),
                    "existing_tables_count": len(existing_tables),
                    "proposed_at": datetime.now().isoformat()
                }
                
                return json.dumps(enhanced_design, indent=2)
                
            except (json.JSONDecodeError, ValueError) as parse_error:
                logger.warning(f"LLM returned invalid JSON: {str(parse_error)}")
                
        except Exception as llm_error:
            logger.warning(f"LLM table design failed: {str(llm_error)}")
        
        # Fallback: Generate basic table structure
        table_name = f"STG_{subject_area.upper().replace(' ', '_')}_DATA"
        
        # Generate basic DDL
        ddl_lines = [f"CREATE TABLE {table_name} ("]
        ddl_lines.append("  ID NUMBER(38,0) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,")
        
        # Add columns based on requirements
        for i, col_concept in enumerate(columns_list):
            if isinstance(col_concept, dict):
                col_name = col_concept.get('name', f'COLUMN_{i+1}')
                col_type = col_concept.get('type', 'VARCHAR(255)')
            else:
                col_name = str(col_concept).upper().replace(' ', '_')
                col_type = 'VARCHAR(255)'
            
            ddl_lines.append(f"  {col_name} {col_type},")
        
        # Add audit columns
        ddl_lines.extend([
            "  CREATED_DATE DATE DEFAULT SYSDATE,",
            "  UPDATED_DATE DATE DEFAULT SYSDATE"
        ])
        
        ddl_lines.append(");")
        
        fallback_design = {
            "status": "proposed",
            "subject_area": subject_area,
            "required_granularity": required_granularity,
            "required_columns": columns_list,
            "table_name": table_name,
            "table_type": "STAGING",
            "ddl_script": "\n".join(ddl_lines),
            "justification": f"Basic staging table for {subject_area} data with identity key and audit columns",
            "recommended_relationships": [],
            "data_model_impact": f"New staging table to support {subject_area} data requirements",
            "existing_tables_count": len(existing_tables),
            "proposed_at": datetime.now().isoformat(),
            "note": "Fallback design used due to LLM generation failure"
        }
        
        return json.dumps(fallback_design, indent=2)
        
    except Exception as e:
        logger.error(f"Error proposing new table structure: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to propose new table structure: {str(e)}"
        })


@mcp.tool()
async def get_catalog_overview() -> str:
    """Get an overview of the data catalog with statistics and available subject areas.
    
    Returns:
        JSON string with catalog overview and statistics
    """
    try:
        stats = get_catalog_stats()
        subject_areas = get_all_subject_areas()
        
        # Get table type breakdown
        catalog = load_data_catalog()
        schema_breakdown = {}
        
        for schema in catalog.get('schemas', []):
            schema_name = schema['schemaName']
            schema_breakdown[schema_name] = {
                'table_count': len(schema.get('tables', [])),
                'table_types': {}
            }
            
            for table in schema.get('tables', []):
                table_type = table.get('tableType', 'Unknown')
                schema_breakdown[schema_name]['table_types'][table_type] = \
                    schema_breakdown[schema_name]['table_types'].get(table_type, 0) + 1
        
        overview = {
            "status": "success",
            "catalog_statistics": stats,
            "subject_areas": subject_areas,
            "schema_breakdown": schema_breakdown,
            "capabilities": [
                "Column mapping analysis",
                "Granularity fit assessment", 
                "Join path discovery",
                "Semantic column matching",
                "ETL logic generation",
                "New table structure proposal"
            ],
            "last_updated": stats.get('cache_timestamp')
        }
        
        return json.dumps(overview, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting catalog overview: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": f"Failed to get catalog overview: {str(e)}"
        })


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


def main():
    """Main entry point for the MCP Data Mapping Analyst Server"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='MCP Data Mapping Analyst Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8003, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    try:
        # Validate metadata files exist
        metadata_dir = "/home/vijay/text2sql_react/data_mapping_metadata"
        catalog_file = f"{metadata_dir}/data_catalog.json"
        mappings_file = f"{metadata_dir}/data_mappings.json"
        
        if not os.path.exists(catalog_file):
            logger.error(f"Data catalog file not found: {catalog_file}")
            sys.exit(1)
            
        if not os.path.exists(mappings_file):
            logger.error(f"Data mappings file not found: {mappings_file}")
            sys.exit(1)
        
        # Test loading metadata
        try:
            load_data_catalog(force_reload=True)
            load_data_mappings(force_reload=True)
            logger.info("Metadata files loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load metadata: {str(e)}")
            sys.exit(1)
        
        # Get the MCP server from FastMCP
        mcp_server = mcp._mcp_server  # noqa: WPS437
        
        # Create Starlette app with SSE support
        starlette_app = create_starlette_app(mcp_server, debug=args.debug)
        
        logger.info(f"Starting MCP Data Mapping Analyst Server on {args.host}:{args.port}")
        uvicorn.run(starlette_app, host=args.host, port=args.port)
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
