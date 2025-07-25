"""
Vector Database Management routes for Text2SQL application.
Provides UI and API endpoints for managing the vector database.
"""

from flask import Blueprint, render_template, request, jsonify, session
import logging
import traceback
from src.utils.vector_store import VectorStore
from src.routes.auth_routes import admin_required, permission_required
from src.models.user import Permissions
from src.utils.user_manager import UserManager
from sentence_transformers import SentenceTransformer
import time
import numpy as np
import json

# Configure logger
logger = logging.getLogger('text2sql.routes.vector_db')

# Create a Blueprint for vector database routes
vector_db_bp = Blueprint('vector_db', __name__, url_prefix='/admin')

# Initialize user manager
user_manager = UserManager()

# Initialize vector store
vector_store = VectorStore()

# Initialize embedding model for text search
embedding_model = None

def convert_numpy_types(obj):
    """Convert NumPy types to native Python types for JSON serialization"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    else:
        return obj

@vector_db_bp.route('/vector-db')
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def vector_db_page():
    """Render the vector database management page"""
    logger.debug("Vector database management page requested")
    return render_template('admin/vector_db.html', available_templates=['admin/vector_db.html'])

@vector_db_bp.route('/api/vector-db/collections', methods=['GET'])
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def get_collections():
    """Get all collections in the vector database"""
    try:
        # Make sure we're connected to the vector database
        if not vector_store.client:
            if not vector_store.connect():
                return jsonify({
                    'success': False,
                    'error': 'Failed to connect to vector database'
                }), 500
        
        # Get all collections
        collections = vector_store.list_collections()
        
        return jsonify({
            'success': True,
            'collections': collections
        })
    except Exception as e:
        logger.exception(f"Error retrieving vector database collections: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@vector_db_bp.route('/api/vector-db/collections/<collection_name>', methods=['GET'])
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def get_collection_details(collection_name):
    """Get details about a specific collection"""
    try:
        # Make sure we're connected to the vector database
        if not vector_store.client:
            if not vector_store.connect():
                return jsonify({
                    'success': False,
                    'error': 'Failed to connect to vector database'
                }), 500
        
        # Check if collection exists
        collections = vector_store.list_collections()
        
        if collection_name not in collections:
            return jsonify({
                'success': False,
                'error': f'Collection {collection_name} does not exist'
            }), 404
        
        # Get collection info using vector store method
        collection_info = vector_store.get_collection_metadata(collection_name)
        
        # Get collection statistics (simplified for ChromaDB)
        stats = {
            'row_count': collection_info.get('count', 0)
        }
        
        return jsonify({
            'success': True,
            'collection_info': collection_info,
            'collection_stats': stats
        })
    except Exception as e:
        logger.exception(f"Error retrieving collection details: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@vector_db_bp.route('/api/vector-db/collections', methods=['POST'])
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def create_collection():
    """Create a new collection"""
    try:
        data = request.get_json()
        if not data or 'collection_name' not in data or 'dimension' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing collection name or dimension'
            }), 400
        
        collection_name = data.get('collection_name')
        dimension = int(data.get('dimension'))
        description = data.get('description', '')
        
        # Make sure we're connected to the vector database
        if not vector_store.client:
            if not vector_store.connect():
                return jsonify({
                    'success': False,
                    'error': 'Failed to connect to vector database'
                }), 500
        
        # Check if collection already exists
        collections = vector_store.list_collections()
        
        if collection_name in collections:
            return jsonify({
                'success': False,
                'error': f'Collection {collection_name} already exists'
            }), 400
        
        # Use the vector_store to create collection
        success = vector_store.init_collection(collection_name, dimension)
        
        if not success:
            return jsonify({
                'success': False,
                'error': f'Failed to create collection {collection_name}'
            }), 500
        
        # Log the action
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='create_vector_collection',
            details=f"Created vector collection: {collection_name} with dimension {dimension}",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': f'Collection {collection_name} created successfully'
        })
    except Exception as e:
        logger.exception(f"Error creating collection: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@vector_db_bp.route('/api/vector-db/collections/<collection_name>', methods=['DELETE'])
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def delete_collection(collection_name):
    """Delete a collection"""
    try:
        # Make sure we're connected to the vector database
        if not vector_store.client:
            if not vector_store.connect():
                return jsonify({
                    'success': False,
                    'error': 'Failed to connect to vector database'
                }), 500
        
        # Check if collection exists
        collections = vector_store.list_collections()
        
        if collection_name not in collections:
            return jsonify({
                'success': False,
                'error': f'Collection {collection_name} does not exist'
            }), 404
        
        # Delete the collection
        if not vector_store.delete_collection(collection_name):
            return jsonify({
                'success': False,
                'error': f'Failed to delete collection {collection_name}'
            }), 500
        
        # Log the action
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='delete_vector_collection',
            details=f"Deleted vector collection: {collection_name}",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': f'Collection {collection_name} deleted successfully'
        })
    except Exception as e:
        logger.exception(f"Error deleting collection: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@vector_db_bp.route('/api/vector-db/collections/<collection_name>/data', methods=['GET'])
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def get_collection_data(collection_name):
    """Get data from a collection"""
    try:
        logger.info(f"GET_COLLECTION_DATA: Requesting data for collection {collection_name}")
        
        # Make sure we're connected to the vector database
        if not vector_store.client:
            if not vector_store.connect():
                return jsonify({
                    'success': False,
                    'error': 'Failed to connect to vector database'
                }), 500
        
        # Check if collection exists
        collections = vector_store.list_collections()
        logger.info(f"GET_COLLECTION_DATA: Available collections: {collections}")
        logger.info(f"GET_COLLECTION_DATA: Looking for collection: {collection_name}")
        
        if collection_name not in collections:
            logger.error(f"GET_COLLECTION_DATA: Collection {collection_name} not found in {collections}")
            return jsonify({
                'success': False,
                'error': f'Collection {collection_name} does not exist'
            }), 404
        
        # Get query parameters
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        # Get filter data - expect JSON filter, not string
        filter_data = request.args.get('filter', None)
        filter_expr = None
        
        # Parse JSON filter if provided
        if filter_data:
            try:
                filter_expr = json.loads(filter_data)
            except json.JSONDecodeError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid filter format. Expected JSON filter.'
                }), 400
        
        # Get collection data using our vector_store methods
        try:
            if filter_expr:
                # Use query_by_filter for filtered results
                all_results = vector_store.query_by_filter(
                    collection_name=collection_name,
                    filter_expr=filter_expr,
                    limit=limit + offset  # Get more results to handle offset
                )
                # Apply offset manually
                results = all_results[offset:offset + limit] if len(all_results) > offset else []
                total_count = len(all_results)
            else:
                # Use list_entries for all results
                all_results = vector_store.list_entries(
                    collection_name=collection_name,
                    limit=limit + offset  # Get more results to handle offset
                )
                # Apply offset manually
                results = all_results[offset:offset + limit] if len(all_results) > offset else []
                total_count = vector_store.count(collection_name)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Failed to retrieve data: {str(e)}'
            }), 500
        
        # Convert NumPy types to native Python types for JSON serialization
        results = convert_numpy_types(results)
        
        return jsonify({
            'success': True,
            'data': results,
            'total': total_count,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.exception(f"Error retrieving collection data: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@vector_db_bp.route('/api/vector-db/collections/<collection_name>/data/<int:id>', methods=['DELETE'])
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def delete_collection_data(collection_name, id):
    """Delete a specific record from a collection"""
    try:
        # Make sure we're connected to the vector database
        if not vector_store.client:
            if not vector_store.connect():
                return jsonify({
                    'success': False,
                    'error': 'Failed to connect to vector database'
                }), 500
        
        # Check if collection exists
        collections = vector_store.list_collections()
        
        if collection_name not in collections:
            return jsonify({
                'success': False,
                'error': f'Collection {collection_name} does not exist'
            }), 404
        
        # Delete the record using our vector_store method
        if vector_store.delete_embedding(collection_name, id):
            # Log the action
            user_manager.log_audit_event(
                user_id=session.get('user_id'),
                action='delete_vector_record',
                details=f"Deleted record ID {id} from vector collection: {collection_name}",
                ip_address=request.remote_addr
            )
            
            return jsonify({
                'success': True,
                'message': f'Record {id} deleted successfully from collection {collection_name}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Failed to delete record {id} from collection {collection_name}'
            }), 500
    except Exception as e:
        logger.exception(f"Error deleting record: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@vector_db_bp.route('/api/vector-db/collections/<collection_name>/search', methods=['POST'])
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def search_collection(collection_name):
    """Search for similar vectors in a collection"""
    global embedding_model
    
    try:
        data = request.get_json()
        if not data or 'search_text' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing search text'
            }), 400
        
        search_text = data.get('search_text')
        limit = data.get('limit', 50)
        filter_data = data.get('filter', None)
        
        # Use filter as ChromaDB JSON filter directly
        filter_expr = filter_data if filter_data else None
        
        # Make sure we're connected to the vector database
        if not vector_store.client:
            if not vector_store.connect():
                return jsonify({
                    'success': False,
                    'error': 'Failed to connect to vector database'
                }), 500
        
        # Check if collection exists
        collections = vector_store.list_collections()
        
        if collection_name not in collections:
            return jsonify({
                'success': False,
                'error': f'Collection {collection_name} does not exist'
            }), 404
        
        # Use ChromaDB's built-in search functionality (no need for separate embedding model)
        try:
            # Use our search_by_text method which leverages ChromaDB's built-in embedding
            results = vector_store.search_by_text(
                collection_name=collection_name,
                query_text=search_text,
                limit=limit,
                filter_expr=filter_expr
            )
            
            # Convert NumPy types to native Python types for JSON serialization
            results = convert_numpy_types(results)
            
            # Log first result for debugging
            if results:
                logger.info(f"Search returned {len(results)} results for '{search_text[:50]}...'")
            
            return jsonify({
                'success': True,
                'results': results,
                'total': len(results),
                'search_text': search_text
            })
            
        except Exception as search_error:
            logger.error(f"Search error: {str(search_error)}")
            return jsonify({
                'success': False,
                'error': f'Search failed: {str(search_error)}'
            }), 500
            
    except Exception as e:
        logger.exception(f"Error searching collection: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@vector_db_bp.route('/api/vector-db/collections/<collection_name>/upload', methods=['POST'])
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def upload_collection_data(collection_name):
    """Upload data to a collection and generate embeddings"""
    try:
        # Log upload attempt with detailed request information
        logger.info(f"Upload attempt to collection: {collection_name}")
        logger.info(f"Form data: {request.form}")
        logger.info(f"Files: {request.files.keys()}")
        
        # Check if file is in the request
        if 'file' not in request.files:
            logger.error(f"No file provided in upload to {collection_name}")
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            logger.error(f"Empty filename in upload to {collection_name}")
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        logger.info(f"Processing file: {file.filename} for collection: {collection_name}")
        
        # Get text field name for generating embeddings
        text_field_name = request.form.get('text_field_name')
        if not text_field_name:
            logger.error(f"Missing text_field_name in upload to {collection_name}")
            return jsonify({
                'success': False,
                'error': 'Text field name is required for generating embeddings'
            }), 400
        
        # Check file type
        if not file.filename.lower().endswith(('.csv', '.json')):
            logger.error(f"Unsupported file type: {file.filename} for collection: {collection_name}")
            return jsonify({
                'success': False,
                'error': 'Only CSV and JSON files are supported'
            }), 400
        
        # Make sure we're connected to the vector database
        if not vector_store.client:
            logger.error(f"Vector store client not initialized for collection: {collection_name}")
            if not vector_store.connect():
                logger.error(f"Failed to connect to vector database for collection: {collection_name}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to connect to vector database'
                }), 500
        
        # Check if collection exists
        available_collections = vector_store.list_collections()
        logger.info(f"Available collections: {available_collections}")
        if collection_name not in available_collections:
            logger.error(f"Collection not found: {collection_name}")
            return jsonify({
                'success': False,
                'error': f'Collection {collection_name} does not exist'
            }), 404
        
        # Load embedding model
        global embedding_model
        if embedding_model is None:
            start_time = time.time()
            logger.info("Loading embedding model...")
            embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info(f"Embedding model loaded in {time.time() - start_time:.2f}s")
        
        # Process the file
        file_extension = file.filename.split('.')[-1].lower()
        logger.info(f"Processing file with extension: {file_extension}")
        
        # Parse file content
        records = []
        
        try:
            if file_extension == 'csv':
                # Save to a temporary file for pandas to read
                import pandas as pd
                import tempfile
                import traceback
                
                logger.info("Processing CSV file")
                temp = tempfile.NamedTemporaryFile()
                file.save(temp.name)
                
                try:
                    # Load CSV file
                    df = pd.read_csv(temp.name)
                    logger.debug(f"CSV columns: {list(df.columns)}")
                    logger.debug(f"CSV shape: {df.shape}")
                    records = df.to_dict(orient='records')
                    logger.info(f"Extracted {len(records)} records from CSV")
                except Exception as csv_error:
                    logger.error(f"Error processing CSV file: {str(csv_error)}")
                    logger.error(f"CSV traceback: {traceback.format_exc()}")
                    raise
                finally:
                    # Close temp file
                    temp.close()
                
            elif file_extension == 'json':
                # Load JSON file
                import json
                
                logger.info("Processing JSON file")
                try:
                    # Read file content
                    content = file.read().decode('utf-8')
                    logger.debug(f"JSON content length: {len(content)} characters")
                    
                    # Log a small sample of the raw content for debugging
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    logger.debug(f"JSON content preview: {content_preview}")
                    
                    # Parse JSON
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError as json_parse_error:
                        logger.error(f"JSON parsing error: {str(json_parse_error)}")
                        logger.error(f"Error at line {json_parse_error.lineno}, column {json_parse_error.colno}")
                        logger.error(f"Error document position: {json_parse_error.pos}")
                        # Get context around error location
                        error_context_start = max(0, json_parse_error.pos - 50)
                        error_context_end = min(len(content), json_parse_error.pos + 50)
                        error_context = content[error_context_start:error_context_end]
                        logger.error(f"Context around error: '...{error_context}...'")
                        raise
                    
                    # Check data type and extract records
                    if isinstance(data, list):
                        records = data
                        logger.info(f"Extracted {len(records)} records from JSON array")
                    else:
                        records = [data]
                        logger.info("Extracted 1 record from JSON object")
                    
                    # Validate records structure
                    if records:
                        sample = records[0]
                        if isinstance(sample, dict):
                            logger.debug(f"Sample record keys: {list(sample.keys())}")
                            for key, value in sample.items():
                                value_type = type(value).__name__
                                value_preview = str(value)[:50] + "..." if isinstance(value, str) and len(str(value)) > 50 else str(value)
                                logger.debug(f"Field '{key}': {value_type} = {value_preview}")
                        else:
                            logger.error(f"Expected dict for record, got {type(sample).__name__}")
                except Exception as json_error:
                    logger.error(f"Error processing JSON file: {str(json_error)}")
                    logger.error(f"JSON traceback: {traceback.format_exc()}")
                    raise
        except Exception as file_error:
            logger.error(f"Fatal error processing file {file.filename}: {str(file_error)}")
            return jsonify({
                'success': False,
                'error': f"Error processing file: {str(file_error)}"
            }), 400
        
        # Verify records have the required text field
        if not records:
            return jsonify({
                'success': False,
                'error': 'No records found in file'
            }), 400
        
        if not any(text_field_name in record for record in records):
            return jsonify({
                'success': False,
                'error': f'Text field "{text_field_name}" not found in records'
            }), 400
        
        # Get collection info to determine vector dimension
        collection_info = vector_store.get_collection_metadata(collection_name)
        vector_dimension = None
        
        # Try to get dimension from different possible locations in the API response
        if collection_info:
            # Option 1: Direct dimension property
            if 'dimension' in collection_info:
                vector_dimension = collection_info['dimension']
            # Option 2: From schema fields
            elif 'schema' in collection_info:
                # Look for vector field
                for field in collection_info['schema']:
                    if field.get('type') == 'VECTOR' or field.get('data_type') == 'VECTOR':
                        vector_dimension = field.get('dimension', field.get('params', {}).get('dimension'))
                        break
                    
        if not vector_dimension:
            # If we couldn't find dimension, default to the model's dimension
            vector_dimension = 384  # Default for all-MiniLM-L6-v2
        
        # Generate embeddings and insert records
        inserted_count = 0
        error_count = 0
        
        # Log the first record for debugging
        if records and len(records) > 0:
            logger.debug(f"First record structure: {records[0]}")
            logger.debug(f"First record keys: {list(records[0].keys())}")
            logger.debug(f"Looking for text field: '{text_field_name}'")
        
        # Get collection info to verify schema compatibility
        try:
            collection_metadata = vector_store.get_collection_metadata(collection_name)
            schema_fields = []  # ChromaDB doesn't expose schema in the same way
            logger.debug(f"Collection schema fields: {schema_fields}")
        except Exception as schema_e:
            logger.error(f"Error fetching collection schema: {str(schema_e)}")
            logger.error(f"Schema error traceback: {traceback.format_exc()}")
        
        for record in records:
            try:
                # Check if text field exists in record
                if text_field_name not in record:
                    logger.warning(f"Text field '{text_field_name}' not found in record, skipping")
                    logger.warning(f"Available fields in record: {list(record.keys())}")
                    error_count += 1
                    continue
                
                # Get text for embedding generation
                text = record[text_field_name]
                if not text or not isinstance(text, str):
                    logger.warning(f"Invalid text in field '{text_field_name}', value: {text}, type: {type(text)}")
                    error_count += 1
                    continue
                
                try:
                    # Generate embedding
                    logger.debug(f"Generating embedding for text: '{text[:100]}...' (truncated)")
                    embedding = embedding_model.encode(text).tolist()
                    
                    # Prepare metadata (exclude text from metadata)
                    metadata = {k: v for k, v in record.items() if k != text_field_name}
                    
                    # Generate a unique ID for this record
                    record_id = inserted_count + error_count + 1
                    
                    logger.debug(f"Inserting record {record_id} with metadata: {list(metadata.keys())}")
                    
                    # Insert into collection using the ChromaDB API
                    try:
                        success = vector_store.insert_embedding(
                            collection_name=collection_name,
                            feedback_id=record_id,
                            vector=embedding,
                            query_text=text,
                            metadata=metadata
                        )
                        if success:
                            inserted_count += 1
                        else:
                            error_count += 1
                            logger.error(f"Failed to insert record {record_id}")
                    except Exception as insert_error:
                        logger.error(f"Error inserting record into collection: {str(insert_error)}")
                        logger.error(f"Insert error traceback: {traceback.format_exc()}")
                        error_count += 1
                except Exception as embed_error:
                    logger.error(f"Error generating embedding: {str(embed_error)}")
                    logger.error(f"Embedding error traceback: {traceback.format_exc()}")
                    error_count += 1
                
            except Exception as record_error:
                logger.error(f"Error processing record: {str(record_error)}")
                logger.error(f"Record processing traceback: {traceback.format_exc()}")
                if record:
                    logger.error(f"Problematic record keys: {list(record.keys()) if isinstance(record, dict) else 'Not a dict'}")
                error_count += 1
        
        # Explicitly flush changes and ensure data is committed
        try:
            # ChromaDB automatically handles persistence
            logger.info(f"Data insertion completed for collection {collection_name}")
            # Attempt to force a flush/commit of the data
            # ChromaDB doesn't require manual flush operations
            logger.info(f"ChromaDB handles persistence automatically")
            
            # Force collection to load for immediate visibility
            # ChromaDB doesn't require manual load operations
            logger.info(f"Collection {collection_name} is automatically available")
                
            # For some vector DB implementations, a query might be needed to refresh
            if inserted_count > 0:
                logger.info(f"Running validation query on {collection_name} to ensure visibility")
                # Verify data accessibility by getting collection count
                count = vector_store.count(collection_name)
                logger.debug(f"Collection now contains {count} documents")
        except Exception as commit_error:
            logger.warning(f"Non-critical error during commit operations: {str(commit_error)}")
            logger.warning(traceback.format_exc())
            # Continue execution since this is not critical
        
        # Log the action
        user_manager.log_audit_event(
            user_id=session.get('user_id'),
            action='upload_vector_data',
            details=f"Uploaded data to {collection_name}: {inserted_count} records inserted, {error_count} errors",
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'message': f'{inserted_count} records inserted successfully ({error_count} errors)'
        })
        
    except Exception as e:
        logger.exception(f"Error uploading data: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@vector_db_bp.route('/api/vector-db/test', methods=['GET'])
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def test_vector_db():
    """Test vector database connectivity and collections"""
    try:
        logger.info("TEST_VECTOR_DB: Starting test")
        
        # Test connection
        if not vector_store.client:
            if not vector_store.connect():
                return jsonify({
                    'success': False,
                    'error': 'Failed to connect to vector database'
                }), 500
        
        # Get collections
        collections = vector_store.list_collections()
        logger.info(f"TEST_VECTOR_DB: Collections: {collections}")
        
        # Test specific collection
        if 'schema_metadata' in collections:
            count = vector_store.count('schema_metadata')
            entries = vector_store.list_entries('schema_metadata', limit=3)
            logger.info(f"TEST_VECTOR_DB: schema_metadata count: {count}, entries: {len(entries)}")
        
        return jsonify({
            'success': True,
            'connected': True,
            'collections': collections,
            'schema_metadata_exists': 'schema_metadata' in collections
        })
        
    except Exception as e:
        logger.exception(f"TEST_VECTOR_DB: Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500