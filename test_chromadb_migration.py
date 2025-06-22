#!/usr/bin/env python3
"""
Test script to verify ChromaDB migration functionality
"""

import sys
import os
import logging

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_migration')

def test_vector_store():
    """Test basic VectorStore functionality"""
    try:
        from src.utils.vector_store import VectorStore
        logger.info("Testing VectorStore...")
        
        vs = VectorStore()
        if vs.connect():
            logger.info("✓ VectorStore connection successful")
            
            # Test collection creation
            if vs.init_collection('test_collection'):
                logger.info("✓ Collection creation successful")
                
                # Test insertion
                if vs.insert_embedding('test_collection', 123, [0.1, 0.2, 0.3], 'test query', {'test': 'metadata'}):
                    logger.info("✓ Embedding insertion successful")
                    
                    # Test search
                    results = vs.search_similar('test_collection', [0.1, 0.2, 0.3], limit=1)
                    if results and len(results) > 0:
                        logger.info(f"✓ Search successful: found {len(results)} results")
                        logger.info(f"  Result: {results[0]}")
                        return True
                    else:
                        logger.error("✗ Search failed: no results")
                else:
                    logger.error("✗ Embedding insertion failed")
            else:
                logger.error("✗ Collection creation failed")
        else:
            logger.error("✗ VectorStore connection failed")
        return False
    except Exception as e:
        logger.error(f"✗ VectorStore test failed: {e}")
        return False

def test_feedback_manager():
    """Test FeedbackManager integration"""
    try:
        from src.utils.feedback_manager import FeedbackManager
        logger.info("Testing FeedbackManager...")
        
        fm = FeedbackManager()
        logger.info("✓ FeedbackManager instantiated successfully")
        
        # Test vector store connection
        if fm.vector_store.connect():
            logger.info("✓ FeedbackManager vector store connected")
            return True
        else:
            logger.error("✗ FeedbackManager vector store connection failed")
            return False
    except Exception as e:
        logger.error(f"✗ FeedbackManager test failed: {e}")
        return False

def test_chroma_service():
    """Test ChromaService"""
    try:
        from src.services.chroma_service import ChromaService
        logger.info("Testing ChromaService...")
        
        cs = ChromaService()
        collections = cs.get_collections_info()
        logger.info(f"✓ ChromaService working: found {len(collections)} collections")
        return True
    except Exception as e:
        logger.error(f"✗ ChromaService test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting ChromaDB migration tests...")
    
    tests = [
        ("VectorStore", test_vector_store),
        ("FeedbackManager", test_feedback_manager),
        ("ChromaService", test_chroma_service),
    ]
    
    results = {}
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        results[test_name] = test_func()
    
    # Summary
    logger.info("\n--- Test Summary ---")
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! ChromaDB migration is working correctly.")
        return 0
    else:
        logger.error(f"❌ {total - passed} tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit(main())
