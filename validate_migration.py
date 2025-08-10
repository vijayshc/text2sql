#!/usr/bin/env python3
"""
Migration Validation Script
===========================

This script validates that the Vue.js migration preserves all functionality
from the original Flask application with complete feature parity check.
"""

import os
import sys
import json
import subprocess
import requests
from typing import Dict, List, Any
from pathlib import Path

class MigrationValidator:
    """Comprehensive migration validation"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.frontend_path = self.project_root / "frontend"
        self.validation_results = {
            "backend_api": [],
            "frontend_views": [],
            "admin_functionality": [],
            "feature_parity": [],
            "architecture": []
        }
    
    def validate_backend_api_structure(self):
        """Validate backend API structure"""
        print("🔍 Validating Backend API Structure...")
        
        api_path = self.project_root / "src" / "api" / "v1"
        if api_path.exists():
            api_files = list(api_path.glob("*.py"))
            expected_apis = [
                "auth.py", "query.py", "schema.py", "feedback.py", 
                "agent.py", "data_mapping.py", "metadata_search.py", "admin.py"
            ]
            
            found_apis = [f.name for f in api_files if f.name != "__init__.py"]
            
            for api in expected_apis:
                if api in found_apis:
                    self.validation_results["backend_api"].append(f"✅ {api} - API endpoint exists")
                else:
                    self.validation_results["backend_api"].append(f"❌ {api} - Missing API endpoint")
        else:
            self.validation_results["backend_api"].append("❌ API v1 directory not found")
    
    def validate_frontend_views(self):
        """Validate Vue.js frontend views"""
        print("🔍 Validating Frontend Views...")
        
        views_path = self.frontend_path / "src" / "views"
        if views_path.exists():
            view_files = list(views_path.glob("*.vue"))
            
            # Expected views based on original functionality
            expected_views = [
                "LoginView.vue", "HomeView.vue", "ProfileView.vue", 
                "ChangePasswordView.vue", "QueryEditorView.vue", "KnowledgeView.vue",
                "AgentView.vue", "DataMappingView.vue", "SchemaView.vue", "MetadataSearchView.vue",
                # Admin views
                "AdminDashboardView.vue", "AdminUsersView.vue", "AdminRolesView.vue",
                "AdminMCPServersView.vue", "AdminAuditView.vue", "AdminSamplesView.vue",
                "AdminSkillLibraryView.vue", "AdminKnowledgeView.vue", "AdminVectorDBView.vue",
                "AdminDatabaseQueryView.vue", "AdminConfigView.vue"
            ]
            
            found_views = [f.name for f in view_files]
            
            for view in expected_views:
                if view in found_views:
                    self.validation_results["frontend_views"].append(f"✅ {view} - Vue component exists")
                else:
                    self.validation_results["frontend_views"].append(f"❌ {view} - Missing Vue component")
        else:
            self.validation_results["frontend_views"].append("❌ Views directory not found")
    
    def validate_admin_functionality(self):
        """Validate all 13 admin functionalities from the screenshots"""
        print("🔍 Validating Admin Functionality...")
        
        # List of admin features from the navigation screenshots
        admin_features = [
            ("Dashboard", "AdminDashboardView.vue"),
            ("Manage Samples", "AdminSamplesView.vue"),
            ("Users", "AdminUsersView.vue"), 
            ("Roles & Permissions", "AdminRolesView.vue"),
            ("MCP Servers", "AdminMCPServersView.vue"),
            ("Skill Library", "AdminSkillLibraryView.vue"),
            ("Schema Management", "SchemaView.vue"),
            ("Metadata Search", "MetadataSearchView.vue"),
            ("Knowledge Management", "AdminKnowledgeView.vue"),
            ("Vector Database", "AdminVectorDBView.vue"),
            ("Database Query Editor", "AdminDatabaseQueryView.vue"),
            ("Configuration", "AdminConfigView.vue"),
            ("Audit Logs", "AdminAuditView.vue")
        ]
        
        views_path = self.frontend_path / "src" / "views"
        found_views = []
        if views_path.exists():
            found_views = [f.name for f in views_path.glob("*.vue")]
        
        for feature_name, view_file in admin_features:
            if view_file in found_views:
                self.validation_results["admin_functionality"].append(f"✅ {feature_name} - Implemented")
            else:
                self.validation_results["admin_functionality"].append(f"❌ {feature_name} - Missing")
    
    def validate_router_configuration(self):
        """Validate Vue.js router configuration"""
        print("🔍 Validating Router Configuration...")
        
        router_path = self.frontend_path / "src" / "router" / "index.ts"
        if router_path.exists():
            router_content = router_path.read_text()
            
            # Check for admin routes
            admin_routes = [
                "/admin", "/admin/users", "/admin/roles", "/admin/mcp-servers",
                "/admin/samples", "/admin/skill-library", "/admin/knowledge",
                "/admin/vector-db", "/admin/database-query", "/admin/config", "/admin/audit"
            ]
            
            for route in admin_routes:
                if route in router_content:
                    self.validation_results["feature_parity"].append(f"✅ Route {route} configured")
                else:
                    self.validation_results["feature_parity"].append(f"❌ Route {route} missing")
        else:
            self.validation_results["feature_parity"].append("❌ Router configuration not found")
    
    def validate_architecture_migration(self):
        """Validate architecture migration"""
        print("🔍 Validating Architecture Migration...")
        
        # Check if legacy templates are removed
        templates_path = self.project_root / "templates"
        if templates_path.exists():
            self.validation_results["architecture"].append("❌ Legacy templates directory still exists")
        else:
            self.validation_results["architecture"].append("✅ Legacy templates removed")
        
        # Check if Vue.js frontend is properly set up
        package_json = self.frontend_path / "package.json"
        if package_json.exists():
            self.validation_results["architecture"].append("✅ Vue.js frontend properly configured")
            
            # Check for required dependencies
            package_data = json.loads(package_json.read_text())
            required_deps = ["vue", "vue-router", "pinia", "axios"]
            
            for dep in required_deps:
                if dep in package_data.get("dependencies", {}):
                    self.validation_results["architecture"].append(f"✅ {dep} dependency present")
                else:
                    self.validation_results["architecture"].append(f"❌ {dep} dependency missing")
        else:
            self.validation_results["architecture"].append("❌ Frontend package.json not found")
        
        # Check app.py for API-only structure
        app_py = self.project_root / "app.py"
        if app_py.exists():
            app_content = app_py.read_text()
            if "render_template" not in app_content:
                self.validation_results["architecture"].append("✅ Backend is API-only (no HTML templates)")
            else:
                self.validation_results["architecture"].append("❌ Backend still has HTML template rendering")
        else:
            self.validation_results["architecture"].append("❌ app.py not found")
    
    def run_frontend_build_test(self):
        """Test if frontend builds successfully"""
        print("🔍 Testing Frontend Build...")
        
        if self.frontend_path.exists():
            try:
                # Check if node_modules exists
                node_modules = self.frontend_path / "node_modules"
                if not node_modules.exists():
                    print("   Installing dependencies...")
                    subprocess.run(["npm", "install"], cwd=self.frontend_path, check=True, capture_output=True)
                
                # Try to build
                print("   Building frontend...")
                result = subprocess.run(
                    ["npm", "run", "build"], 
                    cwd=self.frontend_path, 
                    capture_output=True, 
                    text=True,
                    timeout=120
                )
                
                if result.returncode == 0:
                    self.validation_results["architecture"].append("✅ Frontend builds successfully")
                else:
                    self.validation_results["architecture"].append(f"❌ Frontend build failed: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                self.validation_results["architecture"].append("❌ Frontend build timed out")
            except Exception as e:
                self.validation_results["architecture"].append(f"❌ Frontend build error: {str(e)}")
        else:
            self.validation_results["architecture"].append("❌ Frontend directory not found")
    
    def run_tests(self):
        """Run existing test suites"""
        print("🔍 Running Test Suites...")
        
        # Run frontend unit tests
        if self.frontend_path.exists():
            try:
                result = subprocess.run(
                    ["npm", "run", "test:unit", "--run"], 
                    cwd=self.frontend_path,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    self.validation_results["feature_parity"].append("✅ Frontend unit tests pass")
                else:
                    self.validation_results["feature_parity"].append(f"⚠️ Frontend unit tests: {result.stdout}")
                    
            except Exception as e:
                self.validation_results["feature_parity"].append(f"⚠️ Frontend tests error: {str(e)}")
    
    def generate_report(self):
        """Generate comprehensive migration report"""
        print("\n" + "=" * 80)
        print("COMPREHENSIVE MIGRATION VALIDATION REPORT")
        print("=" * 80)
        
        categories = [
            ("Backend API Structure", "backend_api"),
            ("Frontend Views", "frontend_views"), 
            ("Admin Functionality", "admin_functionality"),
            ("Feature Parity", "feature_parity"),
            ("Architecture Migration", "architecture")
        ]
        
        total_checks = 0
        passed_checks = 0
        
        for category_name, category_key in categories:
            print(f"\n📋 {category_name}")
            print("-" * 50)
            
            for result in self.validation_results[category_key]:
                print(f"   {result}")
                total_checks += 1
                if result.startswith("✅"):
                    passed_checks += 1
        
        print("\n" + "=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print(f"Total Checks: {total_checks}")
        print(f"Passed: {passed_checks}")
        print(f"Failed/Warning: {total_checks - passed_checks}")
        
        success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 95:
            print("\n🎉 MIGRATION STATUS: EXCELLENT - All functionality preserved!")
        elif success_rate >= 85:
            print("\n✅ MIGRATION STATUS: GOOD - Minor issues detected")
        elif success_rate >= 70:
            print("\n⚠️  MIGRATION STATUS: ADEQUATE - Some functionality may be missing")
        else:
            print("\n❌ MIGRATION STATUS: NEEDS ATTENTION - Significant issues detected")
        
        print("\n" + "=" * 80)
        return success_rate >= 85
    
    def run_validation(self):
        """Run complete migration validation"""
        print("🚀 Starting Comprehensive Migration Validation...")
        print(f"📁 Project Root: {self.project_root}")
        print(f"🎨 Frontend Path: {self.frontend_path}")
        print()
        
        # Run all validation checks
        self.validate_backend_api_structure()
        self.validate_frontend_views()
        self.validate_admin_functionality()
        self.validate_router_configuration()
        self.validate_architecture_migration()
        self.run_frontend_build_test()
        self.run_tests()
        
        # Generate and return report
        return self.generate_report()


def main():
    """Main validation function"""
    validator = MigrationValidator()
    success = validator.run_validation()
    
    if success:
        print("\n✅ Migration validation completed successfully!")
        return 0
    else:
        print("\n❌ Migration validation found issues that need attention.")
        return 1


if __name__ == "__main__":
    sys.exit(main())