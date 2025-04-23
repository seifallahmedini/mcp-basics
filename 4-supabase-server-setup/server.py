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

load_dotenv("C:/Users/LENOVO/Desktop/100 Days Challenge/mcp-basics/4-supabase-server-setup/.env")

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
def run_sql(request: SQLQueryRequest) -> SQLQueryResponse:
    """
    Run an arbitrary SQL query on the Supabase database.

    Args:
        request (SQLQueryRequest): The SQL query to execute.

    Returns:
        SQLQueryResponse: The query result data.
    """
    # Reason: This uses the Supabase RPC to run SQL. Use with caution.
    result = supabase.rpc("execute_sql", {"sql": request.sql}).execute()
    return SQLQueryResponse(data=result.data)

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

# --- Main entry ---
if __name__ == "__main__":
    transport = "sse"
    if transport == "stdio":
        print("Running server with stdio transport")
        mcp.run(transport="stdio")
    elif transport == "sse":
        print("Running server with SSE transport")
        mcp.run(transport="sse")
    else:
        raise ValueError(f"Unknown transport: {transport}")
