#!/usr/bin/env python3
"""
Test script to validate the conversational support implementation
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.config import KNOWLEDGE_CONVERSATION_HISTORY_LIMIT, METADATA_CONVERSATION_HISTORY_LIMIT

def test_configuration():
    """Test that the conversation history configuration is loaded correctly"""
    print("Testing conversation history configuration...")
    
    print(f"Knowledge conversation history limit: {KNOWLEDGE_CONVERSATION_HISTORY_LIMIT}")
    print(f"Metadata conversation history limit: {METADATA_CONVERSATION_HISTORY_LIMIT}")
    
    assert isinstance(KNOWLEDGE_CONVERSATION_HISTORY_LIMIT, int), "Knowledge history limit should be an integer"
    assert isinstance(METADATA_CONVERSATION_HISTORY_LIMIT, int), "Metadata history limit should be an integer"
    assert KNOWLEDGE_CONVERSATION_HISTORY_LIMIT > 0, "Knowledge history limit should be positive"
    assert METADATA_CONVERSATION_HISTORY_LIMIT > 0, "Metadata history limit should be positive"
    
    print("✓ Configuration test passed!")

def test_knowledge_manager_signature():
    """Test that knowledge manager has the updated get_answer signature"""
    print("\nTesting knowledge manager signature...")
    
    from src.utils.knowledge_manager import KnowledgeManager
    import inspect
    
    # Check the get_answer method signature
    signature = inspect.signature(KnowledgeManager.get_answer)
    params = list(signature.parameters.keys())
    
    expected_params = ['self', 'query', 'user_id', 'stream', 'tags', 'conversation_history']
    
    for param in expected_params:
        assert param in params, f"Missing parameter: {param}"
    
    print("✓ Knowledge manager signature test passed!")

def test_route_imports():
    """Test that the route modules can be imported successfully"""
    print("\nTesting route imports...")
    
    try:
        from src.routes.knowledge_routes import knowledge_bp
        print("✓ Knowledge routes imported successfully")
    except Exception as e:
        print(f"✗ Knowledge routes import failed: {e}")
        return False
    
    try:
        from src.routes.metadata_search_routes import metadata_search_bp
        print("✓ Metadata search routes imported successfully")
    except Exception as e:
        print(f"✗ Metadata search routes import failed: {e}")
        return False
    
    return True

def main():
    print("=== Testing Conversation Support Implementation ===\n")
    
    try:
        test_configuration()
        test_knowledge_manager_signature()
        
        if test_route_imports():
            print("\n✓ All tests passed! Conversation support implementation looks good.")
            return True
        else:
            print("\n✗ Some tests failed. Please check the implementation.")
            return False
            
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
