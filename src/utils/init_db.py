"""
Database initialization utility for Text-to-SQL application.
Creates a sample SQLite database with example tables and data.
"""

import sqlite3
import os
import pandas as pd
from sqlalchemy import create_engine, text

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
            tables_used TEXT                     -- Comma-separated list of tables used
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
        return True
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

if __name__ == "__main__":
    init_sample_db()