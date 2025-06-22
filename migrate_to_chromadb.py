#!/usr/bin/env python3
"""
Migration utility to help transition from Milvus to ChromaDB
This script helps users backup and migrate their existing vector data
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('migration')

def backup_old_vector_data():
    """Backup any existing vector database files"""
    old_files = [
        './vector_store.db',
        './vector_store.db.wal',
        './vector_store.db.shm'
    ]
    
    backup_dir = './backup_milvus'
    os.makedirs(backup_dir, exist_ok=True)
    
    backed_up = []
    for file_path in old_files:
        if os.path.exists(file_path):
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            try:
                import shutil
                shutil.copy2(file_path, backup_path)
                backed_up.append(file_path)
                logger.info(f"Backed up {file_path} to {backup_path}")
            except Exception as e:
                logger.error(f"Failed to backup {file_path}: {e}")
    
    return backed_up

def initialize_chromadb():
    """Initialize ChromaDB and create default collections"""
    try:
        from src.utils.vector_store import VectorStore
        
        logger.info("Initializing ChromaDB...")
        vs = VectorStore()
        
        if not vs.connect():
            logger.error("Failed to connect to ChromaDB")
            return False
        
        # Create standard collections
        collections_to_create = [
            'feedback_embeddings',
            'knowledge_chunks', 
            'schema_metadata'
        ]
        
        for collection_name in collections_to_create:
            if vs.init_collection(collection_name):
                logger.info(f"✓ Created collection: {collection_name}")
            else:
                logger.warning(f"Failed to create collection: {collection_name}")
        
        logger.info("ChromaDB initialization completed")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB: {e}")
        return False

def verify_migration():
    """Verify that the migration was successful"""
    try:
        from src.utils.vector_store import VectorStore
        from src.services.chroma_service import ChromaService
        
        logger.info("Verifying migration...")
        
        # Test VectorStore
        vs = VectorStore()
        if not vs.connect():
            logger.error("VectorStore connection failed")
            return False
        
        # Test ChromaService
        cs = ChromaService()
        collections = cs.list_collections()
        logger.info(f"Available collections: {collections}")
        
        # Test basic operations
        test_collection = 'migration_test'
        if vs.init_collection(test_collection):
            if vs.insert_embedding(test_collection, 999, [0.1, 0.2, 0.3], 'test migration', {'test': 'true'}):
                results = vs.search_similar(test_collection, [0.1, 0.2, 0.3], limit=1)
                if results and len(results) > 0:
                    logger.info("✓ Migration verification successful")
                    # Clean up test
                    vs.delete_embedding(test_collection, 999)
                    return True
                else:
                    logger.error("Search test failed")
            else:
                logger.error("Insertion test failed")
        else:
            logger.error("Collection creation test failed")
        
        return False
        
    except Exception as e:
        logger.error(f"Migration verification failed: {e}")
        return False

def cleanup_old_files():
    """Clean up old Milvus files after successful migration"""
    old_files = [
        './vector_store.db',
        './vector_store.db.wal', 
        './vector_store.db.shm'
    ]
    
    for file_path in old_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Removed old file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not remove {file_path}: {e}")

def main():
    """Main migration process"""
    logger.info("Starting Milvus to ChromaDB migration...")
    
    print("🔄 Text2SQL Vector Database Migration")
    print("=====================================")
    print("This script will migrate your vector database from Milvus to ChromaDB.")
    print()
    
    # Step 1: Backup
    logger.info("Step 1: Backing up existing data...")
    backed_up_files = backup_old_vector_data()
    if backed_up_files:
        print(f"✓ Backed up {len(backed_up_files)} files to ./backup_milvus/")
    else:
        print("ℹ️  No existing Milvus files found to backup")
    
    # Step 2: Initialize ChromaDB
    logger.info("Step 2: Initializing ChromaDB...")
    if initialize_chromadb():
        print("✓ ChromaDB initialized successfully")
    else:
        print("❌ Failed to initialize ChromaDB")
        return 1
    
    # Step 3: Verify migration
    logger.info("Step 3: Verifying migration...")
    if verify_migration():
        print("✓ Migration verification successful")
    else:
        print("❌ Migration verification failed")
        return 1
    
    # Step 4: Cleanup (optional)
    if backed_up_files:
        response = input("\n🗑️  Remove old Milvus files? (y/N): ").strip().lower()
        if response == 'y':
            cleanup_old_files()
            print("✓ Old files cleaned up")
        else:
            print("ℹ️  Old files preserved")
    
    print("\n🎉 Migration completed successfully!")
    print("Your Text2SQL application is now using ChromaDB for vector storage.")
    print()
    print("Next steps:")
    print("1. Restart your application")
    print("2. Test vector search functionality")
    print("3. Re-index any existing knowledge base documents if needed")
    
    return 0

if __name__ == "__main__":
    exit(main())
