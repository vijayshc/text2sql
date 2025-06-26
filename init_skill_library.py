#!/usr/bin/env python3
"""
Initialize MCP Skill Library with sample skills
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from src.models.skill import Skill, SkillCategory, SkillStatus
from src.utils.skill_vectorizer import SkillVectorizer

def load_sample_skills():
    """Load sample skills from JSON file into database and vector store"""
    try:
        # Initialize database table
        logger.info("Creating skills database table...")
        Skill.create_table()
        
        # Load sample skills from JSON file
        sample_file = project_root / "sample_skills.json"
        if not sample_file.exists():
            logger.error(f"Sample skills file not found: {sample_file}")
            return False
        
        logger.info(f"Loading sample skills from {sample_file}")
        with open(sample_file, 'r') as f:
            data = json.load(f)
        
        skills_data = data.get('skills', [])
        if not skills_data:
            logger.error("No skills found in sample file")
            return False
        
        # Initialize skill vectorizer
        logger.info("Initializing skill vectorizer...")
        vectorizer = SkillVectorizer()
        
        # Process each skill
        loaded_count = 0
        for skill_data in skills_data:
            try:
                # Check if skill already exists
                existing_skill = Skill.search_by_name(skill_data['name'])
                if existing_skill:
                    logger.info(f"Skill '{skill_data['name']}' already exists, skipping...")
                    continue
                
                # Create skill object
                skill = Skill(
                    name=skill_data['name'],
                    description=skill_data['description'],
                    category=skill_data['category'],
                    tags=skill_data.get('tags', []),
                    prerequisites=skill_data.get('prerequisites', []),
                    steps=skill_data['steps'],
                    examples=skill_data.get('examples', []),
                    status=skill_data.get('status', SkillStatus.ACTIVE.value),
                    version=skill_data.get('version', '1.0'),
                    created_by='system'
                )
                
                # Save to database
                skill.save()
                logger.info(f"Saved skill: {skill.name}")
                
                # Add to vector store if active
                if skill.status == SkillStatus.ACTIVE.value:
                    vectorizer.add_skill(skill)
                    logger.info(f"Added skill to vector store: {skill.name}")
                
                loaded_count += 1
                
            except Exception as e:
                logger.error(f"Error loading skill '{skill_data.get('name', 'unknown')}': {str(e)}")
        
        logger.info(f"Successfully loaded {loaded_count} skills out of {len(skills_data)} total")
        
        # Get final stats
        stats = vectorizer.get_stats()
        if stats:
            logger.info(f"Vector store stats: {stats}")
        
        return loaded_count > 0
        
    except Exception as e:
        logger.error(f"Error initializing skill library: {str(e)}")
        return False

def main():
    """Main entry point"""
    logger.info("Starting MCP Skill Library initialization...")
    
    success = load_sample_skills()
    
    if success:
        logger.info("MCP Skill Library initialization completed successfully!")
        print("\n✅ MCP Skill Library initialized successfully!")
        print("📊 Sample skills have been loaded into the database and vector store")
        print("🚀 You can now start the MCP Skill Server with: ./start_mcp_skill_server.sh")
        print("🌐 Access the admin panel to manage skills at: http://localhost:5000/admin/skills")
        return 0
    else:
        logger.error("MCP Skill Library initialization failed!")
        print("\n❌ MCP Skill Library initialization failed!")
        print("Check the logs above for error details")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
