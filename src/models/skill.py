"""
Skill model for MCP Skill Library Server.
Handles skill storage and management.
"""

from datetime import datetime
from enum import Enum
import json
import uuid

from src.utils.database import get_db_connection


class SkillCategory(Enum):
    DATA_ENGINEERING = "data_engineering"
    DATA_ANALYSIS = "data_analysis"
    DATABASE_MANAGEMENT = "database_management"
    ETL_PIPELINE = "etl_pipeline"
    MACHINE_LEARNING = "machine_learning"
    AUTOMATION = "automation"
    DEVOPS = "devops"
    REPORTING = "reporting"
    TESTING = "testing"
    INTEGRATION = "integration"
    MONITORING = "monitoring"
    SECURITY = "security"
    OTHER = "other"


class SkillStatus(Enum):
    ACTIVE = "active"
    DRAFT = "draft"  
    DEPRECATED = "deprecated"


class Skill:
    def __init__(self, id=None, skill_id=None, name=None, description=None, 
                 category=None, tags=None, prerequisites=None, steps=None, 
                 examples=None, status=SkillStatus.ACTIVE.value, 
                 version="1.0", created_by=None, created_at=None, updated_at=None):
        """Initialize a Skill object
        
        Args:
            id: Database ID (auto-generated)
            skill_id: Unique skill identifier (UUID)
            name: Skill name
            description: Skill description
            category: Skill category from SkillCategory enum
            tags: List of tags for categorization
            prerequisites: List of prerequisites/requirements
            steps: List of detailed technical steps
            examples: List of usage examples
            status: Skill status from SkillStatus enum
            version: Skill version (semantic versioning)
            created_by: User who created the skill
            created_at: Creation timestamp
            updated_at: Last update timestamp
        """
        
        # Convert string timestamps from DB to datetime
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        self.id = id
        self.skill_id = skill_id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.category = category
        self.tags = tags if isinstance(tags, list) else json.loads(tags) if tags else []
        self.prerequisites = prerequisites if isinstance(prerequisites, list) else json.loads(prerequisites) if prerequisites else []
        self.steps = steps if isinstance(steps, list) else json.loads(steps) if steps else []
        self.examples = examples if isinstance(examples, list) else json.loads(examples) if examples else []
        self.status = status
        self.version = version
        self.created_by = created_by
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()

    @classmethod
    def create_table(cls):
        """Create the skills table if it doesn't exist."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            tags TEXT DEFAULT '[]',
            prerequisites TEXT DEFAULT '[]',
            steps TEXT NOT NULL,
            examples TEXT DEFAULT '[]',
            status TEXT DEFAULT 'active',
            version TEXT DEFAULT '1.0',
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_skills_category ON skills(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_skills_status ON skills(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_skills_skill_id ON skills(skill_id)')
        
        conn.commit()
        conn.close()

    @classmethod
    def get_all(cls, category=None, status=None):
        """Get all skills from the database with optional filters."""
        conn = get_db_connection()
        conn.row_factory = cls._dict_factory
        cursor = conn.cursor()
        
        query = 'SELECT * FROM skills WHERE 1=1'
        params = []
        
        if category:
            query += ' AND category = ?'
            params.append(category)
            
        if status:
            query += ' AND status = ?'
            params.append(status)
            
        query += ' ORDER BY name'
        
        cursor.execute(query, params)
        skills = [cls(**row) for row in cursor.fetchall()]
        
        conn.close()
        return skills

    @classmethod
    def get_by_id(cls, skill_id):
        """Get a skill by skill_id (UUID)."""
        conn = get_db_connection()
        conn.row_factory = cls._dict_factory
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM skills WHERE skill_id = ?', (skill_id,))
        skill_data = cursor.fetchone()
        
        conn.close()
        return cls(**skill_data) if skill_data else None
    
    @classmethod
    def get_by_db_id(cls, db_id):
        """Get a skill by database ID."""
        conn = get_db_connection()
        conn.row_factory = cls._dict_factory
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM skills WHERE id = ?', (db_id,))
        skill_data = cursor.fetchone()
        
        conn.close()
        return cls(**skill_data) if skill_data else None

    @classmethod
    def search_by_name(cls, name_pattern):
        """Search skills by name pattern."""
        conn = get_db_connection()
        conn.row_factory = cls._dict_factory
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM skills WHERE name LIKE ? AND status = ? ORDER BY name', 
                      (f'%{name_pattern}%', SkillStatus.ACTIVE.value))
        skills = [cls(**row) for row in cursor.fetchall()]
        
        conn.close()
        return skills

    @classmethod
    def get_categories_with_counts(cls):
        """Get all categories with skill counts."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT category, COUNT(*) as count 
        FROM skills 
        WHERE status = ? 
        GROUP BY category 
        ORDER BY count DESC, category
        ''', (SkillStatus.ACTIVE.value,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{'category': row[0], 'count': row[1]} for row in results]

    def save(self):
        """Save this skill to the database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if self.id:
            # Update existing record
            self.updated_at = datetime.now()
            cursor.execute('''
            UPDATE skills 
            SET name = ?, description = ?, category = ?, tags = ?, 
                prerequisites = ?, steps = ?, examples = ?, status = ?, 
                version = ?, updated_at = ?
            WHERE id = ?
            ''', (
                self.name,
                self.description,
                self.category,
                json.dumps(self.tags),
                json.dumps(self.prerequisites),
                json.dumps(self.steps),
                json.dumps(self.examples),
                self.status,
                self.version,
                self.updated_at,
                self.id
            ))
        else:
            # Insert new record
            cursor.execute('''
            INSERT INTO skills (skill_id, name, description, category, tags, 
                              prerequisites, steps, examples, status, version, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.skill_id,
                self.name,
                self.description,
                self.category,
                json.dumps(self.tags),
                json.dumps(self.prerequisites),
                json.dumps(self.steps),
                json.dumps(self.examples),
                self.status,
                self.version,
                self.created_by
            ))
            self.id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return self

    def delete(self):
        """Delete this skill from the database."""
        if not self.id:
            return False
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM skills WHERE id = ?', (self.id,))
        
        conn.commit()
        conn.close()
        
        return True

    def to_dict(self):
        """Convert skill to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'skill_id': self.skill_id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'tags': self.tags,
            'prerequisites': self.prerequisites,
            'steps': self.steps,
            'examples': self.examples,
            'status': self.status,
            'version': self.version,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def _dict_factory(cursor, row):
        """Convert row to dictionary for SQLite row factory."""
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def get_searchable_text(self):
        """Get text representation for vector embedding."""
        text_parts = [
            f"Skill: {self.name}",
            f"Category: {self.category.replace('_', ' ').title()}",
            f"Description: {self.description}"
        ]
        
        if self.tags:
            text_parts.append(f"Tags: {', '.join(self.tags)}")
            
        if self.prerequisites:
            text_parts.append(f"Prerequisites: {', '.join(self.prerequisites)}")
            
        if self.steps:
            # Include first few steps for context
            steps_text = ". ".join(self.steps[:3])
            text_parts.append(f"Steps: {steps_text}")
        
        return "\n".join(text_parts)
