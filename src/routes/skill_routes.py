"""
Skill management routes for admin interface
"""

from flask import Blueprint, request, jsonify, render_template
from src.models.skill import Skill, SkillCategory, SkillStatus
from src.utils.skill_vectorizer import SkillVectorizer
from src.routes.auth_routes import admin_required, permission_required
from src.models.user import Permissions
import logging
import json

skill_bp = Blueprint('skill', __name__)
logger = logging.getLogger('text2sql.skill_routes')

# Initialize skill vectorizer (lazy loading)
_skill_vectorizer = None

def get_skill_vectorizer():
    """Get skill vectorizer instance (lazy loading)"""
    global _skill_vectorizer
    if _skill_vectorizer is None:
        _skill_vectorizer = SkillVectorizer()
    return _skill_vectorizer

@skill_bp.route('/skills')
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def skills_page():
    """Skills management page"""
    return render_template('admin/skills.html')

@skill_bp.route('/api/skills', methods=['GET'])
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def list_skills():
    """List all skills with optional filtering"""
    try:
        category = request.args.get('category')
        status = request.args.get('status', SkillStatus.ACTIVE.value)
        
        skills = Skill.get_all(category=category, status=status)
        
        # Convert to dict for JSON serialization
        skills_data = [skill.to_dict() for skill in skills]
        
        return jsonify({
            'success': True,
            'skills': skills_data,
            'total': len(skills_data)
        })
        
    except Exception as e:
        logger.error(f"Error listing skills: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@skill_bp.route('/api/skills/<skill_id>', methods=['GET'])
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def get_skill(skill_id):
    """Get a specific skill by ID"""
    try:
        skill = Skill.get_by_id(skill_id)
        
        if not skill:
            return jsonify({
                'success': False,
                'error': 'Skill not found'
            }), 404
        
        return jsonify({
            'success': True,
            'skill': skill.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error getting skill {skill_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@skill_bp.route('/api/skills', methods=['POST'])
@admin_required
@permission_required(Permissions.MANAGE_USERS)
def create_skill():
    """Create a new skill"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'description', 'category', 'steps']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Validate category
        if data['category'] not in [cat.value for cat in SkillCategory]:
            return jsonify({
                'success': False,
                'error': f'Invalid category: {data["category"]}'
            }), 400
        
        # Create skill
        skill = Skill(
            name=data['name'],
            description=data['description'],
            category=data['category'],
            tags=data.get('tags', []),
            prerequisites=data.get('prerequisites', []),
            steps=data['steps'],
            examples=data.get('examples', []),
            status=data.get('status', SkillStatus.ACTIVE.value),
            version=data.get('version', '1.0'),
            created_by=data.get('created_by', 'admin')
        )
        
        # Save to database
        skill.save()
        
        # Add to vector store if active
        if skill.status == SkillStatus.ACTIVE.value:
            vectorizer = get_skill_vectorizer()
            vectorizer.add_skill(skill)
        
        logger.info(f"Created skill: {skill.name} (ID: {skill.skill_id})")
        
        return jsonify({
            'success': True,
            'skill': skill.to_dict(),
            'message': 'Skill created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating skill: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@skill_bp.route('/api/skills/<skill_id>', methods=['PUT'])
@admin_required
@permission_required(Permissions.MANAGE_USERS)
def update_skill(skill_id):
    """Update an existing skill"""
    try:
        skill = Skill.get_by_id(skill_id)
        
        if not skill:
            return jsonify({
                'success': False,
                'error': 'Skill not found'
            }), 404
        
        data = request.get_json()
        
        # Update fields if provided
        if 'name' in data:
            skill.name = data['name']
        if 'description' in data:
            skill.description = data['description']
        if 'category' in data:
            if data['category'] not in [cat.value for cat in SkillCategory]:
                return jsonify({
                    'success': False,
                    'error': f'Invalid category: {data["category"]}'
                }), 400
            skill.category = data['category']
        if 'tags' in data:
            skill.tags = data['tags']
        if 'prerequisites' in data:
            skill.prerequisites = data['prerequisites']
        if 'steps' in data:
            skill.steps = data['steps']
        if 'examples' in data:
            skill.examples = data['examples']
        if 'status' in data:
            skill.status = data['status']
        if 'version' in data:
            skill.version = data['version']
        
        # Save to database
        skill.save()
        
        # Update vector store
        vectorizer = get_skill_vectorizer()
        if skill.status == SkillStatus.ACTIVE.value:
            vectorizer.update_skill(skill)
        else:
            # Remove from vector store if not active
            vectorizer.remove_skill(skill.skill_id)
        
        logger.info(f"Updated skill: {skill.name} (ID: {skill.skill_id})")
        
        return jsonify({
            'success': True,
            'skill': skill.to_dict(),
            'message': 'Skill updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating skill {skill_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@skill_bp.route('/api/skills/<skill_id>', methods=['DELETE'])
@admin_required
@permission_required(Permissions.MANAGE_USERS)
def delete_skill(skill_id):
    """Delete a skill"""
    try:
        skill = Skill.get_by_id(skill_id)
        
        if not skill:
            return jsonify({
                'success': False,
                'error': 'Skill not found'
            }), 404
        
        skill_name = skill.name
        
        # Remove from vector store
        vectorizer = get_skill_vectorizer()
        vectorizer.remove_skill(skill.skill_id)
        
        # Delete from database
        skill.delete()
        
        logger.info(f"Deleted skill: {skill_name} (ID: {skill_id})")
        
        return jsonify({
            'success': True,
            'message': 'Skill deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting skill {skill_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@skill_bp.route('/api/skills/categories', methods=['GET'])
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def list_categories():
    """List all skill categories with counts"""
    try:
        categories = Skill.get_categories_with_counts()
        
        # Add all available categories (including empty ones)
        all_categories = []
        category_counts = {cat['category']: cat['count'] for cat in categories}
        
        for category in SkillCategory:
            all_categories.append({
                'value': category.value,
                'label': category.value.replace('_', ' ').title(),
                'count': category_counts.get(category.value, 0)
            })
        
        return jsonify({
            'success': True,
            'categories': all_categories
        })
        
    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@skill_bp.route('/api/skills/search', methods=['POST'])
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def search_skills():
    """Search skills using vector search"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        category = data.get('category')
        limit = data.get('limit', 10)
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Query is required'
            }), 400
        
        vectorizer = get_skill_vectorizer()
        
        # Use vector search for skills
        results, search_description = vectorizer.search_skills_vector(query, limit)
        
        return jsonify({
            'success': True,
            'results': results,
            'search_method': search_description,
            'total': len(results)
        })
        
    except Exception as e:
        logger.error(f"Error searching skills: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@skill_bp.route('/api/skills/vectorize', methods=['POST'])
@admin_required
@permission_required(Permissions.MANAGE_USERS)
def vectorize_skills():
    """Reprocess all skills into vector store"""
    try:
        vectorizer = get_skill_vectorizer()
        success = vectorizer.process_all_skills()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Skills vectorization completed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Skills vectorization failed'
            }), 500
        
    except Exception as e:
        logger.error(f"Error vectorizing skills: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@skill_bp.route('/api/skills/stats', methods=['GET'])
@admin_required
@permission_required(Permissions.ADMIN_ACCESS)
def get_skill_stats():
    """Get skill library statistics"""
    try:
        vectorizer = get_skill_vectorizer()
        stats = vectorizer.get_stats()
        
        if stats:
            return jsonify({
                'success': True,
                'stats': stats
            })
        else:
            return jsonify({
                'success': True,
                'stats': {
                    'total_skills': 0,
                    'message': 'No skills found in vector store'
                }
            })
        
    except Exception as e:
        logger.error(f"Error getting skill stats: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@skill_bp.route('/api/skills/import', methods=['POST'])
@admin_required
@permission_required(Permissions.MANAGE_USERS)
def import_skills():
    """Import skills from JSON data"""
    try:
        data = request.get_json()
        skills_data = data.get('skills', [])
        
        if not skills_data:
            return jsonify({
                'success': False,
                'error': 'No skills data provided'
            }), 400
        
        imported_count = 0
        errors = []
        
        vectorizer = get_skill_vectorizer()
        
        for skill_data in skills_data:
            try:
                # Validate required fields
                required_fields = ['name', 'description', 'category', 'steps']
                for field in required_fields:
                    if not skill_data.get(field):
                        raise ValueError(f'Missing required field: {field}')
                
                # Create skill
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
                    created_by=skill_data.get('created_by', 'admin')
                )
                
                # Save to database
                skill.save()
                
                # Add to vector store if active
                if skill.status == SkillStatus.ACTIVE.value:
                    vectorizer.add_skill(skill)
                
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Error importing skill '{skill_data.get('name', 'unknown')}': {str(e)}")
        
        return jsonify({
            'success': True,
            'imported_count': imported_count,
            'total_provided': len(skills_data),
            'errors': errors,
            'message': f'Successfully imported {imported_count} skills'
        })
        
    except Exception as e:
        logger.error(f"Error importing skills: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
