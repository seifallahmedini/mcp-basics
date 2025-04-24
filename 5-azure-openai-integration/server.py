"""
Supabase MCP Server: Exposes tools to interact with a Supabase database.

Features:
- List tables
- (To be added) Insert, update, delete rows, run SQL

Follows PEP8, uses pydantic V2, and FastMCP for APIs.
"""
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os
from typing import List, Any, Dict
from pydantic import BaseModel, field_validator
from supabase import create_client, Client

load_dotenv("../.env")

# --- Supabase connection setup ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Pydantic models ---
class ListTablesResponse(BaseModel):
    tables: List[str]

class SQLQueryRequest(BaseModel):
    sql: str

    @field_validator('sql')
    @classmethod
    def validate_sql(cls, v: str, info) -> str:
        if not v.strip():
            raise ValueError("SQL query must not be empty.")
        return v

class SQLQueryResponse(BaseModel):
    data: Any

class TableRowRequest(BaseModel):
    table: str
    row: dict

class TableRowUpdateRequest(BaseModel):
    table: str
    match: dict
    values: dict

class TableRowDeleteRequest(BaseModel):
    table: str
    match: dict

class TableRowResponse(BaseModel):
    data: Any

class BulkInsertRequest(BaseModel):
    table: str
    rows: List[Dict[str, Any]]

    @field_validator('rows')
    @classmethod
    def validate_rows(cls, v, info):
        if not v or not isinstance(v, list):
            raise ValueError("Rows must be a non-empty list of dictionaries.")
        return v

class BulkUpdateRequest(BaseModel):
    table: str
    match: Dict[str, Any]
    values: Dict[str, Any]

    @field_validator('values')
    @classmethod
    def validate_values(cls, v, info):
        if not v or not isinstance(v, dict):
            raise ValueError("Values must be a non-empty dictionary.")
        return v

class FilterRequest(BaseModel):
    table: str
    filters: Dict[str, Any]
    limit: int = 10

    @field_validator('filters')
    @classmethod
    def validate_filters(cls, v, info):
        if not isinstance(v, dict):
            raise ValueError("Filters must be a dictionary.")
        return v

class SearchRequest(BaseModel):
    table: str
    column: str
    query: str
    limit: int = 10

    @field_validator('column')
    @classmethod
    def validate_column(cls, v, info):
        if not v or not isinstance(v, str):
            raise ValueError("Column must be a non-empty string.")
        return v

# --- MCP server setup ---
mcp = FastMCP(
    name="SupabaseTools",
    host="0.0.0.0",
    port=3000,
)

@mcp.tool()
def list_tables() -> ListTablesResponse:
    """
    List all tables in the public schema of the Supabase database.

    Returns:
        ListTablesResponse: List of table names.
    """
    # Reason: Supabase REST API does not expose information_schema, so we use a custom RPC.
    result = supabase.rpc("list_public_tables").execute()
    tables = [row["table_name"] for row in result.data] if result.data else []
    return ListTablesResponse(tables=tables)

@mcp.tool()
def insert_row(request: TableRowRequest) -> TableRowResponse:
    """
    Insert a row into a Supabase table.

    Args:
        request (TableRowRequest): Table name and row data.

    Returns:
        TableRowResponse: Inserted row data or error.
    """
    # Reason: Uses Supabase Python client for type-safe insert.
    result = supabase.table(request.table).insert(request.row).execute()
    return TableRowResponse(data=result.data)

@mcp.tool()
def update_row(request: TableRowUpdateRequest) -> TableRowResponse:
    """
    Update rows in a Supabase table matching criteria.

    Args:
        request (TableRowUpdateRequest): Table, match criteria, and new values.

    Returns:
        TableRowResponse: Updated row data or error.
    """
    # Reason: Uses Supabase Python client for type-safe update.
    result = supabase.table(request.table).update(request.values).match(request.match).execute()
    return TableRowResponse(data=result.data)

@mcp.tool()
def delete_row(request: TableRowDeleteRequest) -> TableRowResponse:
    """
    Delete rows from a Supabase table matching criteria.

    Args:
        request (TableRowDeleteRequest): Table and match criteria.

    Returns:
        TableRowResponse: Deleted row data or error.
    """
    # Reason: Uses Supabase Python client for type-safe delete.
    result = supabase.table(request.table).delete().match(request.match).execute()
    return TableRowResponse(data=result.data)

@mcp.tool()
def get_table_schema(table: str) -> Dict[str, Any]:
    """
    Get the schema (columns and types) for a given table via the execute_sql RPC.

    Args:
        table (str): Table name.

    Returns:
        dict: Mapping of column_name -> data_type, or an error message.
    """
    # 1. Validate to prevent SQL injection
    if not table.isidentifier():
        return {"error": "Invalid table name."}

    # 2. Build the SQL without a trailing semicolon
    sql = (
        f"SELECT column_name, data_type "
        f"FROM information_schema.columns "
        f"WHERE table_schema = 'public' AND table_name = '{table}'"
    )

    # 3. Call the RPC, catching any execution errors
    try:
        response = supabase.rpc("execute_sql", {"query_text": sql}).execute()
        data = response.data
    except Exception as e:
        return {"error": f"Error executing SQL: {str(e)}"}

    # 4. Validate that we received a non-empty list
    if not data or not isinstance(data, list):
        return {"error": f"No schema found for table '{table}'."}

    # 5. Unpack the JSONB array from the first element
    if not data:
        return {"data": []}
    # Return the data as a list of dicts with 'column_name' and 'data_type'
    return {"data": [
        {"column_name": col["column_name"], "data_type": col["data_type"]}
        for col in data
    ]}

@mcp.tool()
def get_row_count(table: str) -> int:
    """
    Get the number of rows in a table.

    Args:
        table (str): Table name.

    Returns:
        int: Number of rows in the table.
    """
    sql = f"SELECT COUNT(*) as count FROM {table};"
    result = supabase.rpc("execute_sql", {"sql": sql}).execute()
    if not result.data or not isinstance(result.data, list):
        return 0
    return result.data[0].get("count", 0)

@mcp.tool()
def get_table_sample(table: str, limit: int = 5) -> Any:
    """
    Get a sample of rows from a table.

    Args:
        table (str): Table name.
        limit (int): Number of rows to sample (default 5).

    Returns:
        Any: List of sample rows.
    """
    result = supabase.table(table).select("*").limit(limit).execute()
    return result.data

@mcp.tool()
def bulk_insert(request: BulkInsertRequest) -> TableRowResponse:
    """
    Insert multiple rows into a Supabase table.

    Args:
        request (BulkInsertRequest): Table name and list of row data.

    Returns:
        TableRowResponse: Inserted rows data or error.
    """
    result = supabase.table(request.table).insert(request.rows).execute()
    return TableRowResponse(data=result.data)

@mcp.tool()
def bulk_update(request: BulkUpdateRequest) -> TableRowResponse:
    """
    Update multiple rows in a Supabase table matching criteria.

    Args:
        request (BulkUpdateRequest): Table, match criteria, and new values.

    Returns:
        TableRowResponse: Updated rows data or error.
    """
    result = supabase.table(request.table).update(request.values).match(request.match).execute()
    return TableRowResponse(data=result.data)

@mcp.tool()
def search_rows(request: SearchRequest) -> TableRowResponse:
    """
    Search for rows in a table where a column contains a query string (case-insensitive).

    Args:
        request (SearchRequest): Table name, column, query string, and optional limit.

    Returns:
        TableRowResponse: Matching rows.
    """
    result = (
        supabase.table(request.table)
        .select("*")
        .ilike(request.column, f"%{request.query}%")
        .limit(request.limit)
        .execute()
    )
    return TableRowResponse(data=result.data)

# --- Main entry ---
if __name__ == "__main__":
    transport = "stdio"
    if transport == "stdio":
        print("Running server with stdio transport")
        mcp.run(transport="stdio")
    elif transport == "sse":
        print("Running server with SSE transport")
        mcp.run(transport="sse")
    else:
        raise ValueError(f"Unknown transport: {transport}")
