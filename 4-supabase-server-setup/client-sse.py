"""
MCP SSE Client for Supabase MCP Server

Connects to the MCP server via SSE transport and demonstrates usage of Supabase tools.
Follows PEP8, uses type hints, and includes Google-style docstrings.
"""
import os
import asyncio
import nest_asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client
from dotenv import load_dotenv

nest_asyncio.apply()  # Needed to run interactive python

load_dotenv("../.env")

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:3000")

"""
Make sure:
1. The Supabase MCP server is running before running this script.
2. The server is configured to use SSE transport.
3. The server is listening on port 3000 (default).

To run the server:
python server.py
"""

def print_result(label: str, result):
    """
    Print the result content from an MCP tool call.

    Args:
        label (str): Description label.
        result: The result object from the tool call.
    """
    try:
        print(f"{label}: {result.content[0].text}")
    except Exception as e:
        print(f"{label}: [Error displaying result] {e}")

async def main():
    """
    Demonstrates calling Supabase MCP tools using SSE transport.
    """
    async with sse_client(f"{MCP_SERVER_URL}/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()

            # List available tools
            tools_result = await session.list_tools()
            print("Available tools:")
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description}")

            # Call list_tables tool
            tables_result = await session.call_tool("list_tables")
            print_result("Tables", tables_result)

            # Example: Insert row (update with your table/fields)
            # insert_result = await session.call_tool("insert_row", arguments={"request": {"table": "your_table", "row": {"field": "value"}}})
            # print_result("Insert Result", insert_result)

            # Example: Update row (update with your table/fields)
            # update_result = await session.call_tool("update_row", arguments={"request": {"table": "your_table", "match": {"id": 1}, "values": {"field": "new_value"}}})
            # print_result("Update Result", update_result)

            # Example: Delete row (update with your table/fields)
            # delete_result = await session.call_tool("delete_row", arguments={"request": {"table": "your_table", "match": {"id": 1}}})
            # print_result("Delete Result", delete_result)

if __name__ == "__main__":
    asyncio.run(main())
