"""
Utility to update the database with knowledge base permissions.
This script adds the necessary permissions for the knowledge base feature
and assigns them to appropriate roles.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.models.user import Role, Permission, UserRole
from src.models.user import Permissions as PermEnum
import logging

# Configure logging
logger = logging.getLogger('text2sql.knowledge_setup')

def setup_knowledge_permissions(db_uri='sqlite:///text2sql.db'):
    """
    Set up knowledge base permissions in the database
    and assign them to appropriate roles.
    
    Args:
        db_uri (str): Database URI
    """
    try:
        # Create engine and session
        engine = create_engine(db_uri)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        logger.info("Setting up knowledge base permissions")
        
        # Define new permissions if they don't exist
        new_permissions = [
            (PermEnum.VIEW_KNOWLEDGE, "Access the knowledge base interface"),
            (PermEnum.USE_KNOWLEDGE, "Query the knowledge base"),
            (PermEnum.MANAGE_KNOWLEDGE, "Manage documents in knowledge base")
        ]
        
        # Add permissions if they don't exist
        for perm_name, description in new_permissions:
            existing = session.query(Permission).filter_by(name=perm_name).first()
            if not existing:
                logger.info(f"Adding permission: {perm_name}")
                new_permission = Permission(name=perm_name, description=description)
                session.add(new_permission)
        
        # Commit to save the new permissions
        session.commit()
        
        # Get references to the permissions and roles
        view_knowledge = session.query(Permission).filter_by(name=PermEnum.VIEW_KNOWLEDGE).first()
        use_knowledge = session.query(Permission).filter_by(name=PermEnum.USE_KNOWLEDGE).first()
        manage_knowledge = session.query(Permission).filter_by(name=PermEnum.MANAGE_KNOWLEDGE).first()
        
        # Get admin and user roles
        admin_role = session.query(Role).filter_by(name=UserRole.ADMIN).first()
        user_role = session.query(Role).filter_by(name=UserRole.USER).first()
        
        # Assign permissions to roles
        if admin_role:
            logger.info("Assigning knowledge permissions to admin role")
            if view_knowledge and view_knowledge not in admin_role.permissions:
                admin_role.permissions.append(view_knowledge)
            if use_knowledge and use_knowledge not in admin_role.permissions:
                admin_role.permissions.append(use_knowledge)
            if manage_knowledge and manage_knowledge not in admin_role.permissions:
                admin_role.permissions.append(manage_knowledge)
        
        if user_role:
            logger.info("Assigning knowledge permissions to user role")
            if view_knowledge and view_knowledge not in user_role.permissions:
                user_role.permissions.append(view_knowledge)
            if use_knowledge and use_knowledge not in user_role.permissions:
                user_role.permissions.append(use_knowledge)
        
        # Commit the changes
        session.commit()
        logger.info("Knowledge base permissions setup complete")
        
        # Close session
        session.close()
        
        return True
    except Exception as e:
        logger.error(f"Error setting up knowledge permissions: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    setup_knowledge_permissions()
