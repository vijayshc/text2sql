#!/usr/bin/env python3
"""
Initialize skill library with sample skills
"""

import sys
import os
import json
import logging

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.models.skill import Skill, SkillStatus
from src.utils.skill_vectorizer import SkillVectorizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_sample_skills():
    """Load sample skills from JSON file into database and vector store"""
    try:
        # Create skill table
        Skill.create_table()
        logger.info("Skill table created/verified")
        
        # Load sample skills from JSON file
        sample_file = os.path.join(project_root, 'sample_skills.json')
        if not os.path.exists(sample_file):
            logger.error(f"Sample skills file not found: {sample_file}")
            return False
        
        with open(sample_file, 'r') as f:
            data = json.load(f)
        
        skills_data = data.get('skills', [])
        if not skills_data:
            logger.error("No skills found in sample file")
            return False
        
        logger.info(f"Loading {len(skills_data)} sample skills...")
        
        # Initialize vectorizer
        vectorizer = SkillVectorizer()
        
        # Check if skills already exist
        existing_skills = Skill.get_all()
        if existing_skills:
            logger.info(f"Found {len(existing_skills)} existing skills")
            response = input("Skills already exist. Do you want to clear and reload? (y/n): ")
            if response.lower() != 'y':
                logger.info("Skipping skill loading")
                return True
            
            # Clear existing skills
            for skill in existing_skills:
                skill.delete()
            logger.info("Cleared existing skills")
            
            # Clear vector store
            vectorizer.vector_store.clear_collection('skills')
            logger.info("Cleared vector store")
        
        # Load skills
        loaded_count = 0
        for skill_data in skills_data:
            try:
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
                
                # Add to vector store
                if skill.status == SkillStatus.ACTIVE.value:
                    vectorizer.add_skill(skill)
                
                loaded_count += 1
                logger.info(f"Loaded skill: {skill.name}")
                
            except Exception as e:
                logger.error(f"Error loading skill '{skill_data.get('name', 'unknown')}': {str(e)}")
        
        logger.info(f"Successfully loaded {loaded_count}/{len(skills_data)} skills")
        
        # Get statistics
        stats = vectorizer.get_stats()
        if stats:
            logger.info(f"Vector store statistics: {stats}")
        
        return loaded_count > 0
        
    except Exception as e:
        logger.error(f"Error loading sample skills: {str(e)}")
        return False

def main():
    """Main entry point"""
    logger.info("Initializing skill library with sample skills...")
    
    success = load_sample_skills()
    
    if success:
        logger.info("Skill library initialization completed successfully!")
        print("\nSkill library is ready!")
        print("You can now:")
        print("1. Start the main application and navigate to Admin > Skill Library")
        print("2. Start the MCP Skill Server: ./start_mcp_skill_server.sh")
        print("3. Add the MCP Skill Server to your agent configuration")
    else:
        logger.error("Skill library initialization failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
