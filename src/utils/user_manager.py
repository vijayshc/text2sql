"""
User management utility for Text2SQL application.
Handles user authentication, role management, and audit logging.
"""

from src.utils.database import get_db_session
from src.models.user import User, Role, Permission, AuditLog, Permissions as PermEnum
import datetime
import uuid
import bcrypt  # Replacing hashlib with bcrypt
import secrets
import logging
import hashlib  # Keep for backward compatibility

logger = logging.getLogger('text2sql')

class UserManager:
    """Manages users, roles, permissions, and audit logs"""
    
    def __init__(self):
        """Initialize the user manager"""
        self.session = get_db_session()
    
    def _hash_password(self, password):
        """Hash a password using bcrypt"""
        # Generate a salt and hash the password
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt(rounds=12)  # Work factor of 12 (higher is more secure but slower)
        password_hash = bcrypt.hashpw(password_bytes, salt)
        return password_hash.decode('utf-8')
    
    def _verify_password(self, password_hash, password):
        """Verify a password against stored hash"""
        if not password_hash or not password:
            return False
            
        try:
            # Check if this is an old SHA-256 hash (contains a $ separator)
            if '$' in password_hash and not password_hash.startswith('$2b$'):
                # Old hash format - verify using old method and upgrade if correct
                salt, stored_hash = password_hash.split('$')
                h = hashlib.sha256()
                h.update((password + salt).encode('utf-8'))
                is_valid = h.hexdigest() == stored_hash
                
                # If valid, update to new hash format
                if is_valid:
                    logger.info("Upgrading password hash from SHA-256 to bcrypt")
                    user = self.session.query(User).filter(User.password_hash == password_hash).first()
                    if user:
                        user.password_hash = self._hash_password(password)
                        self.session.commit()
                
                return is_valid
            
            # New bcrypt hash format
            password_bytes = password.encode('utf-8')
            stored_hash_bytes = password_hash.encode('utf-8')
            return bcrypt.checkpw(password_bytes, stored_hash_bytes)
            
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False
    
    def authenticate(self, username, password):
        """Authenticate a user by username and password"""
        try:
            user = self.session.query(User).filter(User.username == username).first()
            print(user)
            if not user:
                return None
                
            if self._verify_password(user.password_hash, password):
                return user.id
                
            return None
        except Exception as e:
            logger.info(f"Authentication error: {str(e)}")
            return None
    
    def create_user(self, username, email, password):
        """Create a new user"""
        try:
            # Check if username or email already exists
            existing_user = self.session.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing_user:
                if existing_user.username == username:
                    raise ValueError(f"Username '{username}' already exists")
                else:
                    raise ValueError(f"Email '{email}' already exists")
            
            # Create the user
            user = User(
                username=username,
                email=email,
                password_hash=self._hash_password(password),
                is_active=True
            )
            
            self.session.add(user)
            self.session.commit()
            
            return user.id
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            raise
    
    def update_user(self, user_id, username, email, password=None):
        """Update an existing user"""
        try:
            user = self.session.query(User).filter(User.id == user_id).first()
            
            if not user:
                raise ValueError("User not found")
            
            # Check if username or email already exists for another user
            existing_user = self.session.query(User).filter(
                ((User.username == username) | (User.email == email)) &
                (User.id != user_id)
            ).first()
            
            if existing_user:
                if existing_user.username == username:
                    raise ValueError(f"Username '{username}' already exists")
                else:
                    raise ValueError(f"Email '{email}' already exists")
            
            # Update user properties
            user.username = username
            user.email = email
            
            # Update password if provided
            if password:
                user.password_hash = self._hash_password(password)
            
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating user: {str(e)}")
            raise
    
    def delete_user(self, user_id):
        """Delete a user"""
        try:
            user = self.session.query(User).filter(User.id == user_id).first()
            
            if not user:
                raise ValueError("User not found")
            
            # Remove user from roles
            user.roles = []
            
            # Delete the user
            self.session.delete(user)
            self.session.commit()
            
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting user: {str(e)}")
            raise
    
    def get_user_by_id(self, user_id):
        """Get a user by ID"""
        if not user_id:
            return None
            
        return self.session.query(User).filter(User.id == user_id).first()
    
    def get_user_by_username(self, username):
        """Get a user by username"""
        return self.session.query(User).filter(User.username == username).first()
    
    def get_all_users(self):
        """Get all users"""
        return self.session.query(User).all()
    
    def get_user_count(self):
        """Get total user count"""
        return self.session.query(User).count()
    
    def get_username_by_id(self, user_id):
        """Get username by ID"""
        if not user_id:
            return None
            
        user = self.get_user_by_id(user_id)
        return user.username if user else None
    
    def change_password(self, user_id, current_password, new_password):
        """Change a user's password"""
        try:
            user = self.get_user_by_id(user_id)
            
            if not user:
                return False
                
            # Verify current password
            if not self._verify_password(user.password_hash, current_password):
                return False
            
            # Update password
            user.password_hash = self._hash_password(new_password)
            self.session.commit()
            
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error changing password: {str(e)}")
            return False
    
    def generate_reset_token(self, username):
        """Generate a password reset token"""
        try:
            user = self.get_user_by_username(username)
            
            if not user:
                return False
            
            # Generate token
            token = secrets.token_urlsafe(32)
            
            # Store token and expiry
            user.reset_token = token
            user.reset_token_expiry = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            
            self.session.commit()
            
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error generating reset token: {str(e)}")
            return False
    
    def verify_reset_token(self, token):
        """Verify a password reset token"""
        try:
            user = self.session.query(User).filter(
                (User.reset_token == token) &
                (User.reset_token_expiry > datetime.datetime.utcnow())
            ).first()
            
            if not user:
                return None
                
            return user.id
        except Exception as e:
            logger.error(f"Error verifying reset token: {str(e)}")
            return None
    
    def reset_password(self, user_id, new_password):
        """Reset a user's password using a token"""
        try:
            user = self.get_user_by_id(user_id)
            
            if not user:
                return False
            
            # Update password
            user.password_hash = self._hash_password(new_password)
            
            # Clear reset token
            user.reset_token = None
            user.reset_token_expiry = None
            
            self.session.commit()
            
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error resetting password: {str(e)}")
            return False
    
    # Role management
    
    def get_all_roles(self):
        """Get all roles"""
        return self.session.query(Role).all()
    
    def get_role_count(self):
        """Get total role count"""
        return self.session.query(Role).count()
    
    def has_role(self, user_id, role_name):
        """Check if a user has a specific role"""
        try:
            user = self.get_user_by_id(user_id)
            
            if not user:
                return False
                
            for role in user.roles:
                if role.name == role_name:
                    return True
                    
            return False
        except Exception as e:
            logger.error(f"Error checking role: {str(e)}")
            return False
    
    def add_user_to_role(self, user_id, role_id):
        """Add a user to a role"""
        try:
            user = self.get_user_by_id(user_id)
            role = self.session.query(Role).filter(Role.id == role_id).first()
            
            if not user or not role:
                return False
            
            # Check if user already has this role
            for existing_role in user.roles:
                if existing_role.id == role.id:
                    return True
            
            # Add role to user
            user.roles.append(role)
            self.session.commit()
            
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error adding user to role: {str(e)}")
            return False
    
    def remove_user_from_role(self, user_id, role_id):
        """Remove a user from a role"""
        try:
            user = self.get_user_by_id(user_id)
            role = self.session.query(Role).filter(Role.id == role_id).first()
            
            if not user or not role:
                return False
            
            # Check if user has this role
            has_role = False
            for existing_role in user.roles:
                if existing_role.id == role.id:
                    has_role = True
                    break
            
            if not has_role:
                return True
            
            # Remove role from user
            user.roles.remove(role)
            self.session.commit()
            
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error removing user from role: {str(e)}")
            return False
    
    def get_role_by_id(self, role_id):
        """Get a role by its ID"""
        try:
            return self.session.query(Role).filter(Role.id == role_id).first()
        except Exception as e:
            logger.error(f"Error getting role by ID: {str(e)}")
            return None
    
    def create_role(self, name, description=""):
        """Create a new role"""
        try:
            # Check if role already exists
            existing_role = self.session.query(Role).filter(Role.name == name).first()
            
            if existing_role:
                raise ValueError(f"Role '{name}' already exists")
            
            # Create the role
            role = Role(name=name, description=description)
            
            self.session.add(role)
            self.session.commit()
            
            return role.id
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error creating role: {str(e)}")
            raise
    
    def update_role(self, role_id, name, description):
        """Update an existing role"""
        try:
            role = self.get_role_by_id(role_id)
            
            if not role:
                raise ValueError("Role not found")
            
            # Check if name already exists for another role
            existing_role = self.session.query(Role).filter(
                (Role.name == name) & (Role.id != role_id)
            ).first()
            
            if existing_role:
                raise ValueError(f"Role name '{name}' already exists")
            
            # Update role properties
            role.name = name
            role.description = description
            
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating role: {str(e)}")
            raise
    
    def delete_role(self, role_id):
        """Delete a role"""
        try:
            role = self.get_role_by_id(role_id)
            
            if not role:
                raise ValueError("Role not found")
            
            # Remove users from role
            for user in role.users:
                user.roles.remove(role)
            
            # Delete the role
            self.session.delete(role)
            self.session.commit()
            
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error deleting role: {str(e)}")
            raise
    
    def get_role_permissions(self, role_id):
        """Get permissions for a role"""
        try:
            role = self.get_role_by_id(role_id)
            
            if not role:
                raise ValueError("Role not found")
                
            return role.permissions
        except Exception as e:
            logger.error(f"Error getting role permissions: {str(e)}")
            raise
    
    def update_role_permissions(self, role_id, permission_ids):
        """Update permissions for a role"""
        try:
            role = self.get_role_by_id(role_id)
            
            if not role:
                raise ValueError("Role not found")
            
            # Clear existing permissions
            role.permissions = []
            
            # Add new permissions
            for perm_id in permission_ids:
                perm = self.session.query(Permission).filter(Permission.id == perm_id).first()
                if perm:
                    role.permissions.append(perm)
            
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error updating role permissions: {str(e)}")
            raise
    
    # Permission management
    
    def get_all_permissions(self):
        """Get all permissions"""
        return self.session.query(Permission).all()
    
    def has_permission(self, user_id, permission_name):
        """Check if a user has a specific permission"""
        try:
            user = self.get_user_by_id(user_id)
            
            if not user:
                return False
                
            for role in user.roles:
                for permission in role.permissions:
                    if permission.name == permission_name:
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking permission: {str(e)}")
            return False
    
    # Audit log management
    
    def log_audit_event(self, user_id, action, details, ip_address=None, query_text=None, sql_query=None, response=None):
        """Log an audit event"""
        try:
            log = AuditLog(
                user_id=user_id,
                action=action,
                details=details,
                ip_address=ip_address,
                query_text=query_text,
                sql_query=sql_query,
                response=response
            )
            
            self.session.add(log)
            self.session.commit()
            
            return log.id
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error logging audit event: {str(e)}")
            return None
    
    def get_audit_logs(self, page=1, limit=50):
        """Get paginated audit logs"""
        try:
            offset = (page - 1) * limit
            
            logs = self.session.query(AuditLog).order_by(
                AuditLog.timestamp.desc()
            ).offset(offset).limit(limit).all()
            
            total = self.session.query(AuditLog).count()
            
            return logs, total
        except Exception as e:
            logger.error(f"Error retrieving audit logs: {str(e)}")
            return [], 0
    
    def get_audit_log_by_id(self, log_id):
        """Get an audit log by ID"""
        return self.session.query(AuditLog).filter(AuditLog.id == log_id).first()
    
    def export_audit_logs(self, filter_type='all'):
        """Export audit logs for download"""
        try:
            query = self.session.query(AuditLog).order_by(AuditLog.timestamp.desc())
            
            # Apply filter
            if filter_type != 'all':
                query = query.filter(AuditLog.action.like(f"%{filter_type}%"))
            
            return query.all()
        except Exception as e:
            logger.error(f"Error exporting audit logs: {str(e)}")
            return []
    
    def get_query_count_since(self, timestamp):
        """Get count of SQL queries since a timestamp"""
        try:
            return self.session.query(AuditLog).filter(
                (AuditLog.timestamp >= timestamp) &
                (AuditLog.action == 'run_query')
            ).count()
        except Exception as e:
            logger.error(f"Error getting query count: {str(e)}")
            return 0
    
    def get_activity_count_since(self, timestamp):
        """Get count of all activities since a timestamp"""
        try:
            return self.session.query(AuditLog).filter(
                AuditLog.timestamp >= timestamp
            ).count()
        except Exception as e:
            logger.error(f"Error getting activity count: {str(e)}")
            return 0
    
    # Database initialization
    
    def initialize_roles_permissions(self):
        """Initialize default roles and permissions"""
        try:
            # Create permissions
            permissions = {
                PermEnum.VIEW_INDEX: "Access the main application",
                PermEnum.RUN_QUERIES: "Run SQL queries",
                PermEnum.VIEW_SAMPLES: "View sample queries",
                PermEnum.MANAGE_SAMPLES: "Create and edit sample queries",
                PermEnum.VIEW_SCHEMA: "View database schema",
                PermEnum.MANAGE_SCHEMA: "Modify database schema",
                PermEnum.ADMIN_ACCESS: "Access admin interface",
                PermEnum.MANAGE_USERS: "Manage users",
                PermEnum.MANAGE_ROLES: "Manage roles and permissions",
                PermEnum.VIEW_AUDIT_LOGS: "View audit logs"
            }
            
            created_permissions = {}
            
            for name, description in permissions.items():
                perm = self.session.query(Permission).filter(Permission.name == name).first()
                
                if not perm:
                    perm = Permission(name=name, description=description)
                    self.session.add(perm)
                    self.session.flush()  # Get the ID without committing
                
                created_permissions[name] = perm
            
            # Create roles
            admin_role = self.session.query(Role).filter(Role.name == "admin").first()
            if not admin_role:
                admin_role = Role(name="admin", description="Administrator with full access")
                self.session.add(admin_role)
                self.session.flush()
                
                # Assign all permissions to admin
                for perm in created_permissions.values():
                    admin_role.permissions.append(perm)
            
            user_role = self.session.query(Role).filter(Role.name == "user").first()
            if not user_role:
                user_role = Role(name="user", description="Standard user")
                self.session.add(user_role)
                self.session.flush()
                
                # Assign basic permissions to standard user
                user_permissions = [
                    PermEnum.VIEW_INDEX,
                    PermEnum.RUN_QUERIES,
                    PermEnum.VIEW_SAMPLES,
                    PermEnum.VIEW_SCHEMA
                ]
                
                for perm_name in user_permissions:
                    user_role.permissions.append(created_permissions[perm_name])
            
            # Create default admin user if not exists
            print("creating admin user")
            admin_user = self.session.query(User).filter(User.username == "admin").first()
            if not admin_user:
                admin_user = User(
                    username="admin",
                    email="admin@example.com",
                    password_hash=self._hash_password("admin123"),
                    is_active=True
                )
                self.session.add(admin_user)
                self.session.flush()
                
                # Assign admin role
                admin_user.roles.append(admin_role)
            
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            logger.error(f"Error initializing roles and permissions: {str(e)}")
            return False