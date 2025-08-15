#!/usr/bin/env python3
"""
Debug test script to check mixture pattern step by step.
"""

import asyncio
import sys
import os
import traceback
import time

# Add the project root to the path
sys.path.insert(0, '/home/vijay/gitrepo/copilot/text2sql')

from src.models.agent_team import AgentTeam
from src.models.execution_method import ExecutionMethod
from src.services.autogen_runtimes.mixture import run_mixture


async def debug_mixture_pattern():
    """Debug the mixture pattern step by step."""
    print("🔍 Debugging mixture pattern...")
    
    # Create test team
    timestamp = str(int(time.time()))
    config = {
        "agents": [
            {
                "name": "Economic_Analyst",
                "role": "analyst", 
                "system_prompt": "You are an economic analyst who evaluates financial and market impacts.",
                "tools": []
            },
            {
                "name": "Social_Strategist",
                "role": "strategist",
                "system_prompt": "You are a social strategist who considers societal and cultural factors.",
                "tools": []
            }
        ],
        "settings": {"max_rounds": 2}
    }
    
    team = AgentTeam(name=f"debug_mixture_team_{timestamp}", description="Debug team for mixture pattern", config=config)
    team.save()
    
    try:
        # Create method
        method = ExecutionMethod(
            name=f"debug_mixture_{timestamp}",
            description="Debug mixture pattern",
            type="mixture",
            team_id=team.id,
            config={"max_rounds": 2}
        )
        method.save()
        
        task = "Analyze the impact of remote work on productivity and employee satisfaction."
        
        print(f"Team ID: {team.id}")
        print(f"Method ID: {method.id}")
        print(f"Task: {task}")
        print(f"Team config: {team.config}")
        
        # Call the mixture pattern directly
        print("\n🔍 Calling run_mixture directly...")
        result = await run_mixture(team, method, task, monitor=None)
        
        print(f"\n📊 Direct result: {result}")
        
        # Clean up
        method.delete()
        return result.get('success', False)
        
    except Exception as e:
        print(f"Exception: {e}")
        traceback.print_exc()
        return False
        
    finally:
        team.delete()


async def main():
    print("🚀 Debugging mixture pattern implementation...")
    
    # Initialize tables
    AgentTeam.create_table()
    ExecutionMethod.create_table()
    
    success = await debug_mixture_pattern()
    
    if success:
        print("\n✅ Debug test PASSED!")
    else:
        print("\n❌ Debug test FAILED!")
    
    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Debug interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Debug failed: {e}")
        traceback.print_exc()
        sys.exit(1)
