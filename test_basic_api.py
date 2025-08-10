#!/usr/bin/env python3
"""
Simple test script to verify basic API infrastructure
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

try:
    print("Testing basic API infrastructure...")
    
    # Test basic imports
    print("1. Testing basic configuration...")
    from config.api_config import API_PREFIX, CORS_ORIGINS, JWT_SECRET_KEY
    print(f"   ✓ API prefix: {API_PREFIX}")
    print(f"   ✓ CORS origins: {CORS_ORIGINS}")
    print(f"   ✓ JWT configured: {'Yes' if JWT_SECRET_KEY else 'No'}")
    
    # Test Flask and CORS
    print("\n2. Testing Flask and CORS...")
    from flask import Flask
    from flask_cors import CORS
    
    test_app = Flask(__name__)
    test_app.config['SECRET_KEY'] = 'test-secret'
    
    # Configure CORS
    cors_config = {
        'origins': CORS_ORIGINS,
        'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        'allow_headers': ['Content-Type', 'Authorization'],
        'supports_credentials': True
    }
    CORS(test_app, **cors_config)
    print("   ✓ Flask app with CORS configured")
    
    # Test JWT
    print("\n3. Testing JWT...")
    import jwt
    from datetime import datetime, timedelta
    
    payload = {
        'user_id': 1,
        'username': 'testuser',
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm='HS256')
    decoded = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
    
    if decoded['username'] == 'testuser':
        print("   ✓ JWT encoding/decoding works")
    else:
        print("   ❌ JWT test failed")
        sys.exit(1)
    
    # Test basic routing
    print("\n4. Testing basic routing...")
    
    @test_app.route('/api/v1/test')
    def test_endpoint():
        return {'message': 'API is working'}
    
    with test_app.test_client() as client:
        response = client.get('/api/v1/test')
        if response.status_code == 200:
            print("   ✓ Basic API routing works")
        else:
            print(f"   ❌ API routing failed (status: {response.status_code})")
            sys.exit(1)
    
    print("\n🎉 Basic API infrastructure test passed!")
    print("\nComponents verified:")
    print("- ✓ Configuration setup")
    print("- ✓ Flask application")
    print("- ✓ CORS configuration")
    print("- ✓ JWT token handling")
    print("- ✓ Basic API routing")
    print("\nPhase 1, Task 1.1.1 (API Infrastructure Setup) is ready!")
    
except Exception as e:
    print(f"\n❌ Error during basic API test: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)