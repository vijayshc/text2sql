#!/usr/bin/env python3
"""
Simple test script to verify mixture pattern works with tools.
"""

import asyncio
import sys
import os
import json
import sqlite3
import logging
import traceback
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from models.models import AgentTeam, ExecutionMethod
from services.autogen_orchestrator import AutoGenOrchestrator
from services.run_monitor import RunMonitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mixture_pattern():
    """Test mixture pattern with tools."""
    print("🧪 Testing mixture pattern with tool integration...")
    
    try:
        # Load configuration from database
        conn = sqlite3.connect('text2sql.db')
        cursor = conn.cursor()
        
        # Get first team
        cursor.execute("SELECT id, name, description, config FROM agent_teams WHERE config IS NOT NULL LIMIT 1")
        team_data = cursor.fetchone()
        
        # Get first method  
        cursor.execute("SELECT id, name, description, config FROM execution_methods LIMIT 1")
        method_data = cursor.fetchone()
        
        conn.close()
        
        if not team_data or not method_data:
            print("❌ No team or method found in database")
            return False
        
        # Create objects
        team_id, team_name, team_desc, team_config_str = team_data
        method_id, method_name, method_desc, method_config_str = method_data
        
        team = AgentTeam(
            id=team_id,
            name=team_name,
            description=team_desc,
            config=json.loads(team_config_str) if team_config_str else {}
        )
        
        method = ExecutionMethod(
            id=method_id,
            name=method_name,
            description=method_desc,
            config=json.loads(method_config_str) if method_config_str else {}
        )
        
        print(f"✅ Using team: {team.name}")
        print(f"✅ Using method: {method.name}")
        print(f"✅ Team config: {team.config}")
        
        # Create orchestrator and monitor
        orchestrator = AutoGenOrchestrator()
        monitor = RunMonitor()
        
        # Test task
        task = "Analyze the weather data for New York and provide insights about temperature trends"
        
        print(f"\n🔄 Running mixture pattern with task: {task}")
        
        # Execute
        start_time = datetime.now()
        result = await orchestrator.run_mixture(team, method, task, monitor)
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        
        # Analyze results
        success = result.get('success', False)
        response = result.get('response', '')
        tools_used = result.get('tools_used', [])
        agents_used = result.get('agents_used', [])
        error = result.get('error')
        
        print(f"\n📊 RESULTS:")
        print(f"   Success: {success}")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Response length: {len(response)} chars")
        print(f"   Tools used: {tools_used}")
        print(f"   Agents used: {agents_used}")
        print(f"   Error: {error}")
        
        if response:
            print(f"\n📝 Response preview:")
            print(f"   {response[:300]}...")
        
        # Check monitor events
        events = monitor.get_events()
        print(f"\n🔍 Monitor events: {len(events)}")
        for event in events[:5]:  # Show first 5 events
            print(f"   {event}")
        
        if success and len(response) > 100:
            print("\n✅ Pattern test PASSED!")
            return True
        else:
            print("\n❌ Pattern test FAILED!")
            return False
            
    except Exception as e:
        print(f"\n💥 Test crashed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False

async def main():
    """Main test execution."""
    success = await test_mixture_pattern()
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
