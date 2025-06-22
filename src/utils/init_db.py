"""
Database initialization utility for Text-to-SQL application.
Creates a sample SQLite database with example tables and data.
"""

import sqlite3
import os
import pandas as pd
from sqlalchemy import create_engine, text
from src.models.user import Base, User, Role, Permission, Permissions
from src.models.configuration import Configuration, ConfigType
from src.utils.user_manager import UserManager
from config.config import (AZURE_ENDPOINT, AZURE_MODEL_NAME, MAX_TOKENS, 
                          TEMPERATURE, CHUNK_SIZE, CHUNK_OVERLAP,
                          OPENROUTER_API_KEY, OPENROUTER_MODEL)

def init_sample_db(db_path='text2sql.db'):
    """Initialize a sample database with example tables and data
    
    Args:
        db_path (str): Path to the SQLite database file
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create full path
        full_path = os.path.abspath(db_path)
        
        # Remove existing database if it exists
        if os.path.exists(full_path):
            os.remove(full_path)
        
        print(f"Creating sample database at {full_path}")
        
        # Create connection
        conn = sqlite3.connect(full_path)
        cursor = conn.cursor()
        
        # Create customers table
        cursor.execute('''
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            country TEXT,
            postal_code TEXT,
            registration_date TEXT
        )
        ''')
        
        # Create products table
        cursor.execute('''
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            price REAL NOT NULL,
            cost REAL,
            stock_quantity INTEGER DEFAULT 0
        )
        ''')
        
        # Create orders table
        cursor.execute('''
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            order_date TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            total_amount REAL,
            FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
        )
        ''')
        
        # Create order_items table
        cursor.execute('''
        CREATE TABLE order_items (
            item_id INTEGER PRIMARY KEY,
            order_id INTEGER,
            product_id INTEGER,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (order_id),
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        )
        ''')
        
        # Create sales_metrics table
        cursor.execute('''
        CREATE TABLE sales_metrics (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            channel TEXT,
            revenue REAL,
            cost REAL,
            profit REAL
        )
        ''')
        
        # Create query_feedback table for storing user feedback on generated SQL
        cursor.execute('''
        CREATE TABLE query_feedback (
            feedback_id INTEGER PRIMARY KEY,
            query_text TEXT NOT NULL,
            sql_query TEXT NOT NULL,
            results_summary TEXT,
            workspace TEXT,
            feedback_rating INTEGER NOT NULL,    -- 1 for thumbs up, 0 for thumbs down
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            embedding BLOB,                      -- For storing vector embeddings for similarity search
            tables_used TEXT,                    -- Comma-separated list of tables used
            is_manual_sample BOOLEAN DEFAULT 0   -- Flag to indicate if this is a manual sample entry
        )
        ''')
        
        print("Tables created successfully")
        
        # Insert sample data for customers
        customers_data = [
            (1, 'John', 'Doe', 'john.doe@example.com', '123-456-7890', '123 Main St', 'New York', 'NY', 'USA', '10001', '2023-01-15'),
            (2, 'Jane', 'Smith', 'jane.smith@example.com', '987-654-3210', '456 Oak Ave', 'Los Angeles', 'CA', 'USA', '90001', '2023-02-20'),
            (3, 'Alice', 'Johnson', 'alice@example.com', '555-123-4567', '789 Pine St', 'Chicago', 'IL', 'USA', '60007', '2023-03-10'),
            (4, 'Bob', 'Williams', 'bob@example.com', '555-987-6543', '101 Maple Dr', 'Houston', 'TX', 'USA', '77002', '2023-01-05'),
            (5, 'Emily', 'Brown', 'emily@example.com', '555-765-4321', '202 Cedar Ln', 'Miami', 'FL', 'USA', '33101', '2023-02-28')
        ]
        
        cursor.executemany('''
        INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', customers_data)
        
        # Insert sample data for products
        products_data = [
            (1, 'Laptop', 'High-performance laptop', 'Electronics', 1299.99, 900.00, 50),
            (2, 'Smartphone', '5G smartphone with high-res camera', 'Electronics', 799.99, 500.00, 100),
            (3, 'Coffee Maker', 'Automatic drip coffee maker', 'Home Appliances', 89.99, 45.00, 30),
            (4, 'Running Shoes', 'Comfortable athletic shoes', 'Apparel', 129.99, 60.00, 80),
            (5, 'Desk Chair', 'Ergonomic office chair', 'Furniture', 249.99, 120.00, 25),
            (6, 'Headphones', 'Noise-cancelling wireless headphones', 'Electronics', 199.99, 100.00, 60),
            (7, 'Blender', 'High-speed countertop blender', 'Home Appliances', 79.99, 40.00, 20),
            (8, 'Backpack', 'Water-resistant laptop backpack', 'Accessories', 59.99, 25.00, 45)
        ]
        
        cursor.executemany('''
        INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', products_data)
        
        # Insert sample data for orders
        orders_data = [
            (1, 1, '2023-04-01', 'completed', 1299.99),
            (2, 2, '2023-04-05', 'completed', 879.98),
            (3, 3, '2023-04-10', 'completed', 89.99),
            (4, 4, '2023-04-15', 'shipped', 259.98),
            (5, 5, '2023-04-20', 'processing', 249.99),
            (6, 1, '2023-05-02', 'completed', 259.98),
            (7, 2, '2023-05-08', 'shipped', 199.99),
            (8, 3, '2023-05-15', 'processing', 139.98)
        ]
        
        cursor.executemany('''
        INSERT INTO orders VALUES (?, ?, ?, ?, ?)
        ''', orders_data)
        
        # Insert sample data for order_items
        order_items_data = [
            (1, 1, 1, 1, 1299.99),  # Order 1: Laptop
            (2, 2, 2, 1, 799.99),   # Order 2: Smartphone
            (3, 2, 3, 1, 79.99),    # Order 2: Coffee Maker
            (4, 3, 3, 1, 89.99),    # Order 3: Coffee Maker
            (5, 4, 4, 2, 259.98),   # Order 4: Running Shoes x2
            (6, 5, 5, 1, 249.99),   # Order 5: Desk Chair
            (7, 6, 6, 1, 199.99),   # Order 6: Headphones
            (8, 6, 8, 1, 59.99),    # Order 6: Backpack
            (9, 7, 6, 1, 199.99),   # Order 7: Headphones
            (10, 8, 7, 1, 79.99),   # Order 8: Blender
            (11, 8, 8, 1, 59.99)    # Order 8: Backpack
        ]
        
        cursor.executemany('''
        INSERT INTO order_items VALUES (?, ?, ?, ?, ?)
        ''', order_items_data)
        
        # Insert sample data for sales_metrics
        sales_metrics_data = [
            (1, '2023-01', 'Online', 15000.00, 8000.00, 7000.00),
            (2, '2023-02', 'Online', 18000.00, 9500.00, 8500.00),
            (3, '2023-03', 'Online', 22000.00, 11000.00, 11000.00),
            (4, '2023-04', 'Online', 24000.00, 12000.00, 12000.00),
            (5, '2023-05', 'Online', 26000.00, 13000.00, 13000.00),
            (6, '2023-01', 'Retail', 10000.00, 6000.00, 4000.00),
            (7, '2023-02', 'Retail', 12000.00, 7000.00, 5000.00),
            (8, '2023-03', 'Retail', 14000.00, 8000.00, 6000.00),
            (9, '2023-04', 'Retail', 15000.00, 8500.00, 6500.00),
            (10, '2023-05', 'Retail', 16000.00, 9000.00, 7000.00)
        ]
        
        cursor.executemany('''
        INSERT INTO sales_metrics VALUES (?, ?, ?, ?, ?, ?)
        ''', sales_metrics_data)
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        print("Sample data inserted successfully")
        
        # Initialize user authentication tables and data using SQLAlchemy
        print("Setting up authentication tables...")
        db_uri = f"sqlite:///{full_path}"
        engine = create_engine(db_uri)
        
        # Import all models that need tables created
        from src.models.configuration import Base as ConfigBase
        
        # Create auth tables and other model tables
        Base.metadata.create_all(engine)
        ConfigBase.metadata.create_all(engine)
        
        # Initialize user manager
        user_manager = UserManager()
        
        # Add the MANAGE_CONFIG permission if it doesn't exist
        try:
            # Check if the permission already exists
            from src.models.user import Permission, Permissions
            session = user_manager._get_session()
            manage_config_exists = session.query(Permission).filter(Permission.name == Permissions.MANAGE_CONFIG).first()
            
            if not manage_config_exists:
                # Create the MANAGE_CONFIG permission
                manage_config_permission = Permission(
                    name=Permissions.MANAGE_CONFIG,
                    description="Permission to view and manage application configurations"
                )
                session.add(manage_config_permission)
                session.commit()
                print("Created MANAGE_CONFIG permission")
                
                # Assign the permission to the admin role
                admin_role = session.query(Role).filter(Role.name == "admin").first()
                if admin_role:
                    manage_config = session.query(Permission).filter(Permission.name == Permissions.MANAGE_CONFIG).first()
                    if manage_config and manage_config not in admin_role.permissions:
                        admin_role.permissions.append(manage_config)
                        session.commit()
                        print("Assigned MANAGE_CONFIG permission to admin role")
                
            # Clear the session to avoid stale data
            session.expire_all()
        except Exception as e:
            print(f"Error setting up MANAGE_CONFIG permission: {e}")
            session = user_manager._get_session()
            session.rollback()

        # Delete existing admin user if exists
        try:
            session = user_manager._get_session()
            existing_admin = session.query(User).filter(User.username == "admin").first()
            
            if existing_admin:
                # Remove all role assignments first
                existing_admin.roles = []
                session.commit()
                
                # Then delete the user
                session.delete(existing_admin)
                session.commit()
                print("Deleted existing admin user")
                
                # Clear the session to avoid stale data
                session.expire_all()
        except Exception as e:
            print(f"Error deleting existing admin user: {e}")
            session = user_manager._get_session()
            session.rollback()

        # Initialize roles and permissions
        if user_manager.initialize_roles_permissions():
            try:
                # Create admin user with credentials
                admin_id = user_manager.create_user(
                    username="admin",
                    email="admin@example.com", 
                    password="admin123"
                )
                
                if admin_id:
                    # Get admin role and assign to user
                    session = user_manager._get_session()
                    admin_role = session.query(Role).filter(Role.name == "admin").first()
                    if admin_role and user_manager.add_user_to_role(admin_id, admin_role.id):
                        print("Admin user recreated successfully (admin/admin123)")
                    else:
                        print("Failed to assign admin role to admin user")
                else:
                    print("Failed to create admin user")
            except Exception as e:
                print(f"Error creating admin user: {e}")
                session = user_manager._get_session()
                session.rollback()
        else:
            print("Failed to initialize authentication system")
            
        # Initialize configuration table and default values
        print("Setting up configurations table...")
        try:
            # Initialize default configuration values
            default_configs = [
                # Azure OpenAI configurations
                Configuration(
                    key="azure_endpoint",
                    value=AZURE_ENDPOINT,
                    value_type=ConfigType.STRING,
                    description="Azure OpenAI API endpoint URL",
                    category="azure",
                    is_sensitive=False
                ),
                Configuration(
                    key="azure_model_name",
                    value=AZURE_MODEL_NAME,
                    value_type=ConfigType.STRING,
                    description="Azure OpenAI model name",
                    category="azure",
                    is_sensitive=False
                ),
                
                # OpenRouter configurations
                Configuration(
                    key="openrouter_api_key",
                    value=OPENROUTER_API_KEY,
                    value_type=ConfigType.STRING,
                    description="OpenRouter API key for accessing models",
                    category="openrouter",
                    is_sensitive=True
                ),
                Configuration(
                    key="openrouter_model",
                    value=OPENROUTER_MODEL,
                    value_type=ConfigType.STRING,
                    description="Default OpenRouter model to use",
                    category="openrouter",
                    is_sensitive=False
                ),
                
                # Model parameters
                Configuration(
                    key="max_tokens",
                    value=str(MAX_TOKENS),
                    value_type=ConfigType.INTEGER,
                    description="Maximum number of tokens to generate",
                    category="model",
                    is_sensitive=False
                ),
                Configuration(
                    key="temperature",
                    value=str(TEMPERATURE),
                    value_type=ConfigType.FLOAT,
                    description="Sampling temperature for model output",
                    category="model",
                    is_sensitive=False
                ),
                
                # Knowledge base configuration
                Configuration(
                    key="chunk_size",
                    value=str(CHUNK_SIZE),
                    value_type=ConfigType.INTEGER,
                    description="Size of text chunks for knowledge base",
                    category="knowledge",
                    is_sensitive=False
                ),
                Configuration(
                    key="chunk_overlap",
                    value=str(CHUNK_OVERLAP),
                    value_type=ConfigType.INTEGER,
                    description="Overlap between knowledge base chunks",
                    category="knowledge",
                    is_sensitive=False
                ),
            ]
            
            # Add configurations to database
            session = user_manager._get_session()
            for config in default_configs:
                # Check if configuration already exists to avoid duplicates
                existing = session.query(Configuration).filter(Configuration.key == config.key).first()
                if not existing:
                    session.add(config)
            
            session.commit()
            print("Configuration table initialized with default values")
        except Exception as e:
            print(f"Error setting up configuration table: {e}")
            session = user_manager._get_session()
            session.rollback()
        
        return True
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

if __name__ == "__main__":
    init_sample_db()