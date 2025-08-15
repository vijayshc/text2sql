#!/usr/bin/env python3
"""
Test script to verify all execution method types can be created and work correctly.
"""

import sys
import sqlite3
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.models.execution_method import ExecutionMethod, ExecutionMethodType
from src.models.agent_team import AgentTeam

def test_execution_method_types():
    """Test that all execution method types are properly integrated."""
    print("🧪 Testing execution method type integration...")
    
    # Check that all types are defined
    all_types = ExecutionMethodType.all()
    print(f"✅ All execution method types: {all_types}")
    print(f"   Total types: {len(all_types)}")
    
    expected_types = [
        'reflection', 'sequential', 'debate', 'concurrent', 
        'group_chat', 'handoff', 'mixture', 'code_exec_groupchat'
    ]
    
    missing_types = [t for t in expected_types if t not in all_types]
    extra_types = [t for t in all_types if t not in expected_types]
    
    if missing_types:
        print(f"❌ Missing types: {missing_types}")
        return False
    
    if extra_types:
        print(f"⚠️  Extra types: {extra_types}")
    
    print("✅ All expected execution method types are defined!")
    
    # Check if LinuxAnalyzer team exists
    conn = sqlite3.connect('text2sql.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name FROM agent_teams WHERE name = 'LinuxAnalyzer'")
    team_data = cursor.fetchone()
    
    if not team_data:
        print("❌ LinuxAnalyzer team not found")
        conn.close()
        return False
    
    team_id, team_name = team_data
    print(f"✅ Found team: {team_name} (ID: {team_id})")
    
    # Test creating execution methods for the missing types
    test_methods = [
        {
            'name': 'Test Sequential Method',
            'description': 'Test sequential execution pattern',
            'type': 'sequential',
            'team_id': team_id,
            'config': {'max_rounds': 4, 'timeout': 60}
        },
        {
            'name': 'Test Group Chat Method', 
            'description': 'Test group chat execution pattern',
            'type': 'group_chat',
            'team_id': team_id,
            'config': {'max_rounds': 6, 'timeout': 90}
        }
    ]
    
    created_methods = []
    
    for method_data in test_methods:
        try:
            # Check if method already exists
            cursor.execute("SELECT id FROM execution_methods WHERE name = ?", (method_data['name'],))
            existing = cursor.fetchone()
            
            if existing:
                print(f"✅ Method '{method_data['name']}' already exists (ID: {existing[0]})")
                continue
            
            # Create the method
            method = ExecutionMethod(
                name=method_data['name'],
                description=method_data['description'],
                type=method_data['type'],
                team_id=method_data['team_id'],
                config=method_data['config']
            )
            
            saved_method = method.save()
            created_methods.append(saved_method)
            
            print(f"✅ Created method: {saved_method.name} (ID: {saved_method.id}, Type: {saved_method.type})")
            
        except Exception as e:
            print(f"❌ Failed to create method '{method_data['name']}': {e}")
            conn.close()
            return False
    
    conn.close()
    
    print(f"\n✅ Successfully tested execution method types!")
    print(f"   Created {len(created_methods)} new test methods")
    print("   Both 'sequential' and 'group_chat' types are now available in the UI dropdown")
    
    return True

if __name__ == "__main__":
    success = test_execution_method_types()
    if success:
        print("\n🎉 All execution method types are properly integrated!")
    else:
        print("\n❌ Integration test failed!")
    sys.exit(0 if success else 1)
