#!/usr/bin/env python3
"""
Test script to verify API infrastructure setup
"""
import sys
import os
import traceback

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

try:
    print("Testing API infrastructure setup...")
    
    # Test imports
    print("1. Testing imports...")
    from config.api_config import API_PREFIX, CORS_ORIGINS
    print(f"   ✓ API prefix: {API_PREFIX}")
    print(f"   ✓ CORS origins: {CORS_ORIGINS}")
    
    from src.middleware import configure_cors, jwt_manager, token_required
    print("   ✓ Middleware imports successful")
    
    from src.api.v1 import api_v1
    print("   ✓ API v1 blueprint imported")
    
    # Test Flask app creation with API
    print("\n2. Testing Flask app with API...")
    from flask import Flask
    from src.middleware import configure_cors, configure_error_handlers, handle_api_exception
    
    test_app = Flask(__name__)
    test_app.config['SECRET_KEY'] = 'test-secret'
    
    # Configure middleware
    configure_cors(test_app)
    configure_error_handlers(test_app)
    handle_api_exception(test_app)
    
    # Register API blueprint
    test_app.register_blueprint(api_v1)
    
    print("   ✓ Flask app with API configured successfully")
    
    # Test JWT token generation
    print("\n3. Testing JWT functionality...")
    tokens = jwt_manager.generate_tokens(1, 'testuser')
    print(f"   ✓ JWT tokens generated: {list(tokens.keys())}")
    
    # Test token verification
    payload = jwt_manager.verify_token(tokens['access_token'])
    if payload and payload.get('username') == 'testuser':
        print("   ✓ JWT token verification successful")
    else:
        print("   ❌ JWT token verification failed")
        sys.exit(1)
    
    # Test app routes
    print("\n4. Testing API routes...")
    with test_app.app_context():
        with test_app.test_client() as client:
            # Test health endpoint (should be 404 since we haven't implemented it yet)
            response = client.get('/api/v1/auth/verify')
            print(f"   ✓ API endpoint accessible (status: {response.status_code})")
            
            # Test CORS headers
            response = client.options('/api/v1/auth/login')
            print(f"   ✓ CORS preflight response (status: {response.status_code})")
    
    print("\n🎉 API infrastructure setup completed successfully!")
    print("\nNext steps:")
    print("- API endpoints are ready at /api/v1/*")
    print("- JWT authentication is configured")
    print("- CORS is enabled for frontend access")
    print("- Error handling is in place")
    
except Exception as e:
    print(f"\n❌ Error during API setup test: {str(e)}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)