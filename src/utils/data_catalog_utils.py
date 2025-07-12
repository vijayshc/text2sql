"""
Data Catalog Utilities for AI Data Mapping Analyst Agent

Helper functions to load, cache, and query the metadata JSON files
for the data mapping and modeling functionality.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger('text2sql.data_catalog_utils')

# Cache for loaded metadata to avoid repeated file I/O
_catalog_cache = None
_mappings_cache = None
_cache_timestamp = None

# Path to metadata directory
METADATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data_mapping_metadata')


@dataclass
class ColumnInfo:
    """Data class for column information"""
    column_name: str
    data_type: str
    business_name: str
    description: str
    is_nullable: bool
    is_natural_key: bool
    is_pii: bool
    security_classification: str
    tags: List[str]
    valid_value_ranges: str


@dataclass
class TableInfo:
    """Data class for table information"""
    table_name: str
    table_type: str
    business_name: str
    description: str
    subject_area: str
    granularity: str
    primary_key: List[str]
    partition_keys: List[str]
    update_frequency: str
    relationships: List[Dict]
    columns: List[ColumnInfo]


@dataclass
class SchemaInfo:
    """Data class for schema information"""
    schema_name: str
    tables: List[TableInfo]


def load_data_catalog(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load the data catalog from JSON file with caching
    
    Args:
        force_reload: Force reload from file even if cached
        
    Returns:
        Dictionary containing the complete data catalog
    """
    global _catalog_cache, _cache_timestamp
    
    catalog_file = os.path.join(METADATA_DIR, 'data_catalog.json')
    
    # Check if we need to reload
    if _catalog_cache is None or force_reload:
        if os.path.exists(catalog_file):
            logger.info(f"Loading data catalog from {catalog_file}")
            try:
                with open(catalog_file, 'r', encoding='utf-8') as f:
                    _catalog_cache = json.load(f)
                    _cache_timestamp = datetime.now()
                logger.info(f"Data catalog loaded successfully with {len(_catalog_cache.get('schemas', []))} schemas")
            except Exception as e:
                logger.error(f"Error loading data catalog: {str(e)}")
                _catalog_cache = {"schemas": []}
        else:
            logger.warning(f"Data catalog file not found at {catalog_file}")
            _catalog_cache = {"schemas": []}
    
    return _catalog_cache


def load_data_mappings(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load the data mappings from JSON file with caching
    
    Args:
        force_reload: Force reload from file even if cached
        
    Returns:
        Dictionary containing all data mappings
    """
    global _mappings_cache
    
    mappings_file = os.path.join(METADATA_DIR, 'data_mappings.json')
    
    # Check if we need to reload
    if _mappings_cache is None or force_reload:
        if os.path.exists(mappings_file):
            logger.info(f"Loading data mappings from {mappings_file}")
            try:
                with open(mappings_file, 'r', encoding='utf-8') as f:
                    _mappings_cache = json.load(f)
                logger.info(f"Data mappings loaded successfully with {len(_mappings_cache.get('mappings', []))} mappings")
            except Exception as e:
                logger.error(f"Error loading data mappings: {str(e)}")
                _mappings_cache = {"mappings": []}
        else:
            logger.warning(f"Data mappings file not found at {mappings_file}")
            _mappings_cache = {"mappings": []}
    
    return _mappings_cache


def get_table_by_name(table_name: str, schema_name: str = None) -> Optional[Dict]:
    """
    Get table information by name
    
    Args:
        table_name: Name of the table to find
        schema_name: Optional schema name to limit search
        
    Returns:
        Dictionary with table information or None if not found
    """
    catalog = load_data_catalog()
    
    for schema in catalog.get('schemas', []):
        # Skip if schema name specified and doesn't match
        if schema_name and schema['schemaName'] != schema_name:
            continue
            
        for table in schema.get('tables', []):
            if table['tableName'].upper() == table_name.upper():
                # Add schema name to table info for context
                table_copy = table.copy()
                table_copy['schemaName'] = schema['schemaName']
                return table_copy
    
    return None


def get_column_by_name(table_name: str, column_name: str, schema_name: str = None) -> Optional[Dict]:
    """
    Get column information by table and column name
    
    Args:
        table_name: Name of the table
        column_name: Name of the column
        schema_name: Optional schema name to limit search
        
    Returns:
        Dictionary with column information or None if not found
    """
    table = get_table_by_name(table_name, schema_name)
    
    if table:
        for column in table.get('columns', []):
            if column['columnName'].upper() == column_name.upper():
                # Add table context to column info
                column_copy = column.copy()
                column_copy['tableName'] = table['tableName']
                column_copy['schemaName'] = table.get('schemaName')
                return column_copy
    
    return None


def get_tables_by_subject_area(subject_area: str) -> List[Dict]:
    """
    Get all tables for a specific subject area
    
    Args:
        subject_area: Subject area to filter by
        
    Returns:
        List of table dictionaries
    """
    catalog = load_data_catalog()
    tables = []
    
    for schema in catalog.get('schemas', []):
        for table in schema.get('tables', []):
            if table.get('subjectArea', '').upper() == subject_area.upper():
                # Add schema name for context
                table_copy = table.copy()
                table_copy['schemaName'] = schema['schemaName']
                tables.append(table_copy)
    
    return tables


def get_tables_by_type(table_type: str) -> List[Dict]:
    """
    Get all tables of a specific type (FACT, DIMENSION, STAGING, etc.)
    
    Args:
        table_type: Type of table to filter by
        
    Returns:
        List of table dictionaries
    """
    catalog = load_data_catalog()
    tables = []
    
    for schema in catalog.get('schemas', []):
        for table in schema.get('tables', []):
            if table.get('tableType', '').upper() == table_type.upper():
                # Add schema name for context
                table_copy = table.copy()
                table_copy['schemaName'] = schema['schemaName']
                tables.append(table_copy)
    
    return tables


def get_column_mapping(table_name: str, column_name: str) -> Optional[Dict]:
    """
    Get existing mapping for a table and column
    
    Args:
        table_name: Target table name
        column_name: Target column name
        
    Returns:
        Mapping dictionary or None if not found
    """
    mappings = load_data_mappings()
    
    for mapping in mappings.get('mappings', []):
        if (mapping.get('targetTable', '').upper() == table_name.upper() and 
            mapping.get('targetColumn', '').upper() == column_name.upper() and
            mapping.get('status', '').upper() == 'ACTIVE'):
            return mapping
    
    return None


def get_relationships_for_table(table_name: str, schema_name: str = None) -> List[Dict]:
    """
    Get all relationships where the specified table is involved
    
    Args:
        table_name: Name of the table
        schema_name: Optional schema name
        
    Returns:
        List of relationship dictionaries
    """
    table = get_table_by_name(table_name, schema_name)
    
    if table:
        return table.get('relationships', [])
    
    return []


def find_join_path_tables(start_table: str, end_table: str) -> List[str]:
    """
    Find tables that can be used to join from start_table to end_table
    
    Args:
        start_table: Starting table name
        end_table: Target table name
        
    Returns:
        List of table names forming the join path
    """
    # This is a simplified version - a full implementation would use graph algorithms
    catalog = load_data_catalog()
    
    # Build a simple relationship graph
    relationships = {}
    
    for schema in catalog.get('schemas', []):
        for table in schema.get('tables', []):
            table_name = table['tableName']
            relationships[table_name] = []
            
            for rel in table.get('relationships', []):
                relationships[table_name].append(rel['toTable'])
    
    # Simple breadth-first search for direct relationships
    if start_table in relationships:
        for connected_table in relationships[start_table]:
            if connected_table == end_table:
                return [start_table, end_table]
            
            # Check for two-hop relationships
            if connected_table in relationships:
                for second_hop in relationships[connected_table]:
                    if second_hop == end_table:
                        return [start_table, connected_table, end_table]
    
    return []


def get_columns_with_tags(tags: List[str], exact_match: bool = False) -> List[Dict]:
    """
    Find columns that have specific tags
    
    Args:
        tags: List of tags to search for
        exact_match: If True, column must have all tags; if False, any tag matches
        
    Returns:
        List of column dictionaries with table context
    """
    catalog = load_data_catalog()
    matching_columns = []
    
    for schema in catalog.get('schemas', []):
        for table in schema.get('tables', []):
            for column in table.get('columns', []):
                column_tags = [tag.lower() for tag in column.get('tags', [])]
                search_tags = [tag.lower() for tag in tags]
                
                if exact_match:
                    # All tags must be present
                    if all(tag in column_tags for tag in search_tags):
                        column_with_context = column.copy()
                        column_with_context['tableName'] = table['tableName']
                        column_with_context['schemaName'] = schema['schemaName']
                        column_with_context['tableType'] = table.get('tableType')
                        column_with_context['subjectArea'] = table.get('subjectArea')
                        matching_columns.append(column_with_context)
                else:
                    # Any tag matches
                    if any(tag in column_tags for tag in search_tags):
                        column_with_context = column.copy()
                        column_with_context['tableName'] = table['tableName']
                        column_with_context['schemaName'] = schema['schemaName']
                        column_with_context['tableType'] = table.get('tableType')
                        column_with_context['subjectArea'] = table.get('subjectArea')
                        matching_columns.append(column_with_context)
    
    return matching_columns


def get_pii_columns() -> List[Dict]:
    """
    Get all columns marked as PII (Personally Identifiable Information)
    
    Returns:
        List of PII column dictionaries with table context
    """
    catalog = load_data_catalog()
    pii_columns = []
    
    for schema in catalog.get('schemas', []):
        for table in schema.get('tables', []):
            for column in table.get('columns', []):
                if column.get('isPII', False):
                    column_with_context = column.copy()
                    column_with_context['tableName'] = table['tableName']
                    column_with_context['schemaName'] = schema['schemaName']
                    column_with_context['tableType'] = table.get('tableType')
                    column_with_context['subjectArea'] = table.get('subjectArea')
                    pii_columns.append(column_with_context)
    
    return pii_columns


def save_mapping(mapping_data: Dict) -> bool:
    """
    Save a new mapping to the data mappings file
    
    Args:
        mapping_data: Dictionary containing mapping information
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        mappings = load_data_mappings()
        
        # Add timestamp if not provided
        if 'createdAt' not in mapping_data:
            mapping_data['createdAt'] = datetime.now().isoformat() + 'Z'
        if 'updatedAt' not in mapping_data:
            mapping_data['updatedAt'] = datetime.now().isoformat() + 'Z'
        
        # Add to mappings list
        mappings['mappings'].append(mapping_data)
        
        # Save back to file
        mappings_file = os.path.join(METADATA_DIR, 'data_mappings.json')
        with open(mappings_file, 'w', encoding='utf-8') as f:
            json.dump(mappings, f, indent=2, ensure_ascii=False)
        
        # Clear cache to force reload
        global _mappings_cache
        _mappings_cache = None
        
        logger.info(f"Mapping saved successfully for {mapping_data.get('targetTable')}.{mapping_data.get('targetColumn')}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving mapping: {str(e)}")
        return False


def get_all_subject_areas() -> List[str]:
    """
    Get all unique subject areas from the catalog
    
    Returns:
        List of subject area names
    """
    catalog = load_data_catalog()
    subject_areas = set()
    
    for schema in catalog.get('schemas', []):
        for table in schema.get('tables', []):
            subject_area = table.get('subjectArea')
            if subject_area:
                subject_areas.add(subject_area)
    
    return sorted(list(subject_areas))


def get_catalog_stats() -> Dict[str, Any]:
    """
    Get statistics about the data catalog
    
    Returns:
        Dictionary with catalog statistics
    """
    catalog = load_data_catalog()
    mappings = load_data_mappings()
    
    total_schemas = len(catalog.get('schemas', []))
    total_tables = 0
    total_columns = 0
    table_types = {}
    subject_areas = set()
    
    for schema in catalog.get('schemas', []):
        for table in schema.get('tables', []):
            total_tables += 1
            total_columns += len(table.get('columns', []))
            
            table_type = table.get('tableType', 'Unknown')
            table_types[table_type] = table_types.get(table_type, 0) + 1
            
            subject_area = table.get('subjectArea')
            if subject_area:
                subject_areas.add(subject_area)
    
    active_mappings = len([m for m in mappings.get('mappings', []) if m.get('status') == 'ACTIVE'])
    total_mappings = len(mappings.get('mappings', []))
    
    return {
        'schemas': total_schemas,
        'tables': total_tables,
        'columns': total_columns,
        'subject_areas': len(subject_areas),
        'table_types': table_types,
        'active_mappings': active_mappings,
        'total_mappings': total_mappings,
        'cache_timestamp': _cache_timestamp.isoformat() if _cache_timestamp else None
    }
