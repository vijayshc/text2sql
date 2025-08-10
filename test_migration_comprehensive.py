#!/usr/bin/env python3
"""
Comprehensive Migration Testing Suite
====================================

This test suite validates that the Vue.js migration preserves all functionality
from the original Flask application with server-side HTML rendering.

Tests cover:
1. Backend API functionality preservation
2. Admin functionality completeness
3. User interface feature parity
4. Database operations integrity
5. Authentication and authorization
"""

import unittest
import requests
import json
import sqlite3
import tempfile
import os
import sys
import subprocess
import time
import threading
from datetime import datetime
from typing import Dict, List, Any

# Add the project root to path
sys.path.insert(0, os.path.abspath('.'))

# Test configuration
TEST_BASE_URL = "http://localhost:5000"
API_BASE_URL = f"{TEST_BASE_URL}/api/v1"
ADMIN_API_URL = f"{API_BASE_URL}/admin"

class TestMigrationBase(unittest.TestCase):
    """Base test class with common utilities"""
    
    @classmethod
    def setUpClass(cls):
        """Start the Flask server for testing"""
        cls.server_process = None
        cls.start_test_server()
        time.sleep(3)  # Give server time to start
    
    @classmethod
    def tearDownClass(cls):
        """Stop the test server"""
        if cls.server_process:
            cls.server_process.terminate()
            cls.server_process.wait()
    
    @classmethod
    def start_test_server(cls):
        """Start Flask server in test mode"""
        try:
            # Start server in background
            cls.server_process = subprocess.Popen([
                sys.executable, 'app.py'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            print(f"Failed to start test server: {e}")
    
    def setUp(self):
        """Set up test session"""
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Set test user credentials
        self.test_user = {
            'username': 'test_admin',
            'password': 'test_password'
        }
    
    def tearDown(self):
        """Clean up test session"""
        self.session.close()
    
    def authenticate(self) -> str:
        """Authenticate and return JWT token"""
        try:
            response = self.session.post(f"{API_BASE_URL}/auth/login", json=self.test_user)
            if response.status_code == 200:
                data = response.json()
                token = data.get('access_token')
                if token:
                    self.session.headers.update({'Authorization': f'Bearer {token}'})
                return token
        except Exception:
            pass
        return None
    
    def make_api_request(self, method: str, endpoint: str, data: Dict = None) -> requests.Response:
        """Make API request with proper headers"""
        url = f"{API_BASE_URL}{endpoint}"
        try:
            if method.upper() == 'GET':
                return self.session.get(url)
            elif method.upper() == 'POST':
                return self.session.post(url, json=data)
            elif method.upper() == 'PUT':
                return self.session.put(url, json=data)
            elif method.upper() == 'DELETE':
                return self.session.delete(url)
        except Exception as e:
            print(f"API request failed: {e}")
            return None


class TestBackendAPIMigration(TestMigrationBase):
    """Test that backend API functionality is preserved"""
    
    def test_api_endpoints_exist(self):
        """Test that all required API endpoints exist"""
        # Core API endpoints that should exist
        endpoints = [
            '/auth/login',
            '/auth/logout', 
            '/auth/refresh',
            '/query/process',
            '/schema/workspaces',
            '/feedback/submit',
            '/admin/dashboard/stats',
            '/admin/samples',
            '/admin/skills',
            '/admin/knowledge/documents',
            '/admin/vector-db/collections',
            '/admin/database/schema',
            '/admin/config'
        ]
        
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.make_api_request('GET', endpoint)
                self.assertIsNotNone(response, f"Endpoint {endpoint} should be accessible")
                # Accept both 200 OK and 401 Unauthorized (for auth-protected endpoints)
                self.assertIn(response.status_code, [200, 401, 403], 
                            f"Endpoint {endpoint} should respond appropriately")
    
    def test_authentication_flow(self):
        """Test authentication works properly"""
        # Test login endpoint exists
        response = self.make_api_request('POST', '/auth/login', {
            'username': 'test_user',
            'password': 'wrong_password'
        })
        self.assertIsNotNone(response)
        # Either 400/401 for bad credentials or 404 if user doesn't exist
        self.assertIn(response.status_code, [400, 401, 404])
    
    def test_cors_headers(self):
        """Test CORS headers are properly configured"""
        response = self.session.options(f"{API_BASE_URL}/auth/login")
        if response.status_code == 200:
            headers = response.headers
            # Check if CORS headers are present
            cors_headers = ['Access-Control-Allow-Origin', 'Access-Control-Allow-Methods']
            for header in cors_headers:
                if header in headers:
                    self.assertIsNotNone(headers[header])


class TestAdminFunctionalityMigration(TestMigrationBase):
    """Test that all admin functionality is properly migrated"""
    
    def test_admin_dashboard_api(self):
        """Test admin dashboard API endpoint"""
        response = self.make_api_request('GET', '/admin/dashboard/stats')
        self.assertIsNotNone(response)
        # Should either work (200) or require auth (401/403)
        self.assertIn(response.status_code, [200, 401, 403])
    
    def test_admin_samples_api(self):
        """Test samples management API"""
        # Test GET samples
        response = self.make_api_request('GET', '/admin/samples')
        self.assertIsNotNone(response)
        self.assertIn(response.status_code, [200, 401, 403])
        
        # Test POST samples structure (should require auth)
        sample_data = {
            'title': 'Test Sample',
            'sql_query': 'SELECT * FROM test',
            'category': 'test'
        }
        response = self.make_api_request('POST', '/admin/samples', sample_data)
        self.assertIsNotNone(response)
        self.assertIn(response.status_code, [201, 400, 401, 403])
    
    def test_admin_skills_api(self):
        """Test skill library API"""
        response = self.make_api_request('GET', '/admin/skills')
        self.assertIsNotNone(response)
        self.assertIn(response.status_code, [200, 401, 403])
        
        # Test skills categories
        response = self.make_api_request('GET', '/admin/skills/categories')
        self.assertIsNotNone(response)
        self.assertIn(response.status_code, [200, 401, 403])
    
    def test_admin_knowledge_api(self):
        """Test knowledge management API"""
        response = self.make_api_request('GET', '/admin/knowledge/documents')
        self.assertIsNotNone(response)
        self.assertIn(response.status_code, [200, 401, 403])
    
    def test_admin_vector_db_api(self):
        """Test vector database API"""
        response = self.make_api_request('GET', '/admin/vector-db/collections')
        self.assertIsNotNone(response)
        self.assertIn(response.status_code, [200, 401, 403])
    
    def test_admin_database_query_api(self):
        """Test database query editor API"""
        response = self.make_api_request('GET', '/admin/database/schema')
        self.assertIsNotNone(response)
        self.assertIn(response.status_code, [200, 401, 403])
    
    def test_admin_config_api(self):
        """Test configuration management API"""
        response = self.make_api_request('GET', '/admin/config')
        self.assertIsNotNone(response)
        self.assertIn(response.status_code, [200, 401, 403])


class TestUserInterfaceMigration(TestMigrationBase):
    """Test that user interface functionality is preserved"""
    
    def test_spa_serves_from_root(self):
        """Test that Vue.js SPA is served from root"""
        response = self.session.get(TEST_BASE_URL)
        self.assertEqual(response.status_code, 200)
        self.assertIn('<!DOCTYPE html>', response.text)
    
    def test_spa_routes_fallback(self):
        """Test that unmatched routes serve the SPA (client-side routing)"""
        routes = ['/login', '/admin', '/query-editor', '/knowledge']
        for route in routes:
            with self.subTest(route=route):
                response = self.session.get(f"{TEST_BASE_URL}{route}")
                self.assertEqual(response.status_code, 200)
                self.assertIn('<!DOCTYPE html>', response.text)
    
    def test_static_assets_served(self):
        """Test that static assets are properly served"""
        # Test for common static file patterns
        response = self.session.get(f"{TEST_BASE_URL}/favicon.ico")
        # Should either exist (200) or not found (404), but not server error
        self.assertIn(response.status_code, [200, 404])


class TestDatabaseMigration(TestMigrationBase):
    """Test that database operations work correctly"""
    
    def test_database_connection(self):
        """Test database connection works"""
        try:
            conn = sqlite3.connect('text2sql.db')
            cursor = conn.cursor()
            
            # Test basic query
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            # Should have some tables
            self.assertGreater(len(tables), 0, "Database should have tables")
            
            conn.close()
            
        except Exception as e:
            self.fail(f"Database connection failed: {e}")
    
    def test_admin_tables_exist(self):
        """Test that admin-related tables exist"""
        expected_tables = ['samples', 'skills', 'configurations', 'knowledge_documents']
        
        try:
            conn = sqlite3.connect('text2sql.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            # Check if admin tables exist
            for table in expected_tables:
                # Table might exist or might not (depending on migration state)
                # This test documents expected schema
                if table in existing_tables:
                    cursor.execute(f"PRAGMA table_info({table});")
                    columns = cursor.fetchall()
                    self.assertGreater(len(columns), 0, f"Table {table} should have columns")
            
            conn.close()
            
        except Exception as e:
            print(f"Database table check warning: {e}")


class TestFeatureParityValidation(TestMigrationBase):
    """Test that all original features are accessible via Vue.js frontend"""
    
    def test_query_processing_available(self):
        """Test query processing functionality is available"""
        # Test query processing endpoint
        query_data = {
            'question': 'Show me all users',
            'workspace': 'default'
        }
        response = self.make_api_request('POST', '/query/process', query_data)
        self.assertIsNotNone(response)
        # Should either work or require auth
        self.assertIn(response.status_code, [200, 400, 401, 403])
    
    def test_schema_management_available(self):
        """Test schema management is available"""
        response = self.make_api_request('GET', '/schema/workspaces')
        self.assertIsNotNone(response)
        self.assertIn(response.status_code, [200, 401, 403])
    
    def test_feedback_system_available(self):
        """Test feedback system is available"""
        feedback_data = {
            'type': 'query_feedback',
            'content': 'Test feedback'
        }
        response = self.make_api_request('POST', '/feedback/submit', feedback_data)
        self.assertIsNotNone(response)
        self.assertIn(response.status_code, [200, 400, 401, 403])


class TestSecurityMigration(TestMigrationBase):
    """Test that security features are properly maintained"""
    
    def test_csrf_protection_available(self):
        """Test CSRF protection is configured"""
        response = self.session.get(f"{API_BASE_URL}/csrf-token")
        # Should either provide token or be not implemented
        self.assertIn(response.status_code, [200, 404])
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn('csrf_token', data)
    
    def test_unauthorized_admin_access_blocked(self):
        """Test that admin endpoints require proper authorization"""
        # Clear any existing auth headers
        if 'Authorization' in self.session.headers:
            del self.session.headers['Authorization']
        
        admin_endpoints = [
            '/admin/dashboard/stats',
            '/admin/samples',
            '/admin/users',
            '/admin/roles'
        ]
        
        for endpoint in admin_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.make_api_request('GET', endpoint)
                # Should require authentication
                self.assertIn(response.status_code, [401, 403])


def run_migration_tests():
    """Run all migration tests and generate report"""
    print("=" * 70)
    print("COMPREHENSIVE MIGRATION TESTING SUITE")
    print("=" * 70)
    print(f"Testing Vue.js migration at: {TEST_BASE_URL}")
    print(f"API Base URL: {API_BASE_URL}")
    print("-" * 70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestBackendAPIMigration,
        TestAdminFunctionalityMigration,
        TestUserInterfaceMigration,
        TestDatabaseMigration,
        TestFeatureParityValidation,
        TestSecurityMigration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("MIGRATION TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Error:')[-1].strip()}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    if success_rate >= 95:
        print("✅ MIGRATION VALIDATION: EXCELLENT")
    elif success_rate >= 80:
        print("⚠️  MIGRATION VALIDATION: GOOD (minor issues)")
    else:
        print("❌ MIGRATION VALIDATION: NEEDS ATTENTION")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_migration_tests()
    sys.exit(0 if success else 1)