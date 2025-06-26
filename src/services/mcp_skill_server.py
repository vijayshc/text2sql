"""
MCP Skill Library Server - HTTP/SSE implementation
Provides Model Context Protocol interface for skill library functionality
"""

import json
import logging
from typing import Any, Dict, List, Optional

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route

from src.models.skill import Skill
from src.utils.skill_vectorizer import SkillVectorizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('mcp_skill_server')

# Initialize FastMCP server for Skill Library tools (SSE)
mcp = FastMCP("skill-library")

# Initialize skill vectorizer
skill_vectorizer = None

def get_skill_vectorizer():
    """Get skill vectorizer instance with lazy initialization"""
    global skill_vectorizer
    if skill_vectorizer is None:
        skill_vectorizer = SkillVectorizer()
    return skill_vectorizer


@mcp.tool()
async def search_skills(query: str, limit: int = 10) -> str:
    """Search for skills using natural language query.

    Args:
        query: Natural language query to search for relevant skills
        limit: Maximum number of results to return (default: 10)
    """
    try:
        if not query:
            return "Error: Query parameter is required"
        
        # Use vector search for skills (no LLM filtering, pure vector search)
        vectorizer = get_skill_vectorizer()
        results, search_description = vectorizer.search_skills_vector(query, limit)
        
        if not results:
            return f"No skills found matching: {query}"
        
        # Format results for response
        formatted_results = []
        formatted_results.append(f"Search Results for: {query}")
        formatted_results.append(f"Search Description: {search_description}")
        formatted_results.append(f"Total Results: {len(results)}")
        formatted_results.append("=" * 50)
        
        for i, result in enumerate(results, 1):
            skill_info = f"""
{i}. {result.get('name', 'Unknown')} (ID: {result.get('skill_id', 'N/A')})
   Category: {result.get('category', 'Unknown')}
   Description: {result.get('description', 'No description')}
   Tags: {', '.join(result.get('tags', []))}
   Similarity Score: {round(result.get('similarity_score', 0.0), 4)}
   Version: {result.get('version', 'N/A')}
"""
            formatted_results.append(skill_info)
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        logger.error(f"Error searching skills: {str(e)}")
        return f"Search failed: {str(e)}"


@mcp.tool()
async def get_skill_details(skill_id: str) -> str:
    """Get detailed technical steps and information for a specific skill.

    Args:
        skill_id: The unique identifier of the skill to retrieve
    """
    try:
        if not skill_id:
            return "Error: skill_id parameter is required"
        
        # Get skill from database
        skill = Skill.get_by_id(skill_id)
        
        if not skill:
            return f"Skill not found: {skill_id}"
        
        # Format complete skill details
        details = f"""
SKILL DETAILS
=============
Name: {skill.name}
ID: {skill.id}
Category: {skill.category}
Description: {skill.description}
Version: {skill.version}
Status: {skill.status}
Tags: {', '.join(skill.tags) if skill.tags else 'None'}

PREREQUISITES:
{chr(10).join(f"• {prereq}" for prereq in skill.prerequisites) if skill.prerequisites else "None specified"}

TECHNICAL STEPS:
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(skill.steps)) if skill.steps else "No steps defined"}

EXAMPLES:
{chr(10).join(f"• {example}" for example in skill.examples) if skill.examples else "No examples provided"}

USAGE INSTRUCTIONS:
This skill provides step-by-step instructions for {skill.name.lower()}. 
Follow the technical steps in order, ensuring all prerequisites are met.

Created: {skill.created_at}
Updated: {skill.updated_at}
"""
        return details
        
    except Exception as e:
        logger.error(f"Error getting skill details: {str(e)}")
        return f"Failed to get skill details: {str(e)}"


@mcp.tool()
async def list_categories() -> str:
    """List all available skill categories with counts."""
    try:
        # Get categories directly from database
        categories = Skill.get_categories_with_counts()
        
        if not categories:
            return "No skill categories found in the database."
        
        # Format categories
        result = ["SKILL CATEGORIES", "=" * 30]
        
        for cat in categories:
            category_info = f"{cat['category'].replace('_', ' ').title()}: {cat['count']} skills"
            result.append(category_info)
        
        result.append("")
        result.append(f"Total Categories: {len(categories)}")
        
        return "\n".join(result)
        
    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}")
        return f"Failed to list categories: {str(e)}"


@mcp.tool()
async def get_skill_stats() -> str:
    """Get statistics about the skill library."""
    try:
        vectorizer = get_skill_vectorizer()
        stats = vectorizer.get_stats()
        
        if not stats:
            return "No skills found in the library"
        
        # Format stats
        result = ["SKILL LIBRARY STATISTICS", "=" * 35]
        
        for key, value in stats.items():
            if isinstance(value, dict):
                result.append(f"{key.replace('_', ' ').title()}:")
                for sub_key, sub_value in value.items():
                    result.append(f"  {sub_key.replace('_', ' ').title()}: {sub_value}")
            else:
                result.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return "\n".join(result)
        
    except Exception as e:
        logger.error(f"Error getting skill stats: {str(e)}")
        return f"Failed to get skill stats: {str(e)}"


def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can serve the provided mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


def main():
    """Main entry point for the MCP Skill Library Server"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='MCP Skill Library Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8002, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    try:
        # Initialize database tables
        Skill.create_table()
        
        # Get the MCP server from FastMCP
        mcp_server = mcp._mcp_server  # noqa: WPS437
        
        # Create Starlette app with SSE support
        starlette_app = create_starlette_app(mcp_server, debug=args.debug)
        
        logger.info(f"Starting MCP Skill Library Server on {args.host}:{args.port}")
        uvicorn.run(starlette_app, host=args.host, port=args.port)
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
