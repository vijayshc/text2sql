import csv
import json
from typing import Dict, List

def convert_csv_to_schema(csv_file_path: str, output_file_path: str) -> None:
    """
    Convert CSV file to schema.json format
    
    Args:
        csv_file_path (str): Path to input CSV file
        output_file_path (str): Path to output JSON file
    """
    # Initialize schema structure
    schema = {
        "workspaces": []
    }
    
    # Dictionary to hold workspace data
    workspaces: Dict[str, Dict] = {}
    
    # Read CSV file
    with open(csv_file_path, 'r') as csv_file:
        reader = csv.DictReader(csv_file, delimiter='|')
        
        for row in reader:
            workspace_name = row['Workspace Name'].strip()
            workspace_desc = row['Workspace description'].strip()
            table_name = row['Table Name'].strip()
            table_desc = row['Table Description'].strip()
            column_name = row['Column Name'].strip()
            column_desc = row['Column Description'].strip()
            column_type = row['Column Datatype'].strip()
            is_primary = row['IsPrimary'].strip().lower()  # Convert to lowercase for comparison
            
            # Create workspace if it doesn't exist
            if workspace_name not in workspaces:
                workspaces[workspace_name] = {
                    "name": workspace_name,
                    "description": workspace_desc,
                    "tables": {}
                }
            
            # Create table if it doesn't exist in the workspace
            if table_name not in workspaces[workspace_name]["tables"]:
                workspaces[workspace_name]["tables"][table_name] = {
                    "name": table_name,
                    "description": table_desc,
                    "columns": []
                }
            
            # Add column to table
            column = {
                "name": column_name,
                "description": column_desc,
                "datatype": column_type.upper(),
                "is_primary_key": is_primary in ('true', 'yes', '1', 't', 'y')  # Convert various true values
            }
            
            workspaces[workspace_name]["tables"][table_name]["columns"].append(column)
    
    # Convert workspaces dictionary to list format
    for workspace_name, workspace_data in workspaces.items():
        # Convert tables from dict to list
        workspace_data["tables"] = list(workspace_data["tables"].values())
        schema["workspaces"].append(workspace_data)
    
    # Write to JSON file
    with open(output_file_path, 'w') as json_file:
        json.dump(schema, json_file, indent=2)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python csv_to_schema.py <input_csv_file> <output_json_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        convert_csv_to_schema(input_file, output_file)
        print(f"Successfully converted {input_file} to {output_file}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)