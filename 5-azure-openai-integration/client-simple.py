import asyncio
import json
from contextlib import AsyncExitStack
from typing import Any, Dict, List

import os
import nest_asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncAzureOpenAI

# Apply nest_asyncio to allow nested event loops (needed for Jupyter/IPython)
nest_asyncio.apply()

# Load environment variables
load_dotenv("../.env")

AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")

print("ENDPOINT:", os.environ.get("AZURE_OPENAI_ENDPOINT"))
print("API KEY:", os.environ.get("AZURE_OPENAI_API_KEY"))
print("API VERSION:", os.environ.get("AZURE_OPENAI_API_VERSION"))

# Global variables to store session state
session = None
exit_stack = AsyncExitStack()
openai_client = AsyncAzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT
)
model = "gpt-4.1"
stdio = None
write = None

# Short-term memory for chat history (in-memory, not persisted)
chat_history: list[dict[str, str]] = []


async def connect_to_server(server_script_path: str = "server.py"):
    """Connect to an MCP server.

    Args:
        server_script_path: Path to the server script.
    """
    global session, stdio, write, exit_stack

    # Server configuration
    server_params = StdioServerParameters(
        command="python",
        args=[server_script_path],
    )

    # Connect to the server
    stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
    stdio, write = stdio_transport
    session = await exit_stack.enter_async_context(ClientSession(stdio, write))

    # Initialize the connection
    await session.initialize()

    # List available tools
    tools_result = await session.list_tools()
    print("\nConnected to server with tools:")
    for tool in tools_result.tools:
        print(f"  - {tool.name}: {tool.description}")


async def get_mcp_tools() -> List[Dict[str, Any]]:
    """Get available tools from the MCP server in OpenAI format.

    Returns:
        A list of tools in OpenAI format.
    """
    global session

    tools_result = await session.list_tools()
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            },
        }
        for tool in tools_result.tools
    ]


async def process_query(query: str) -> str:
    """
    Process a query using OpenAI and available MCP tools, maintaining short-term memory.

    Args:
        query: The user query.

    Returns:
        The response from OpenAI.
    """
    global session, openai_client, model, chat_history

    # Add user message to chat history
    chat_history.append({"role": "user", "content": query})

    # Get available tools
    tools = await get_mcp_tools()

    # Prepare messages for OpenAI (short-term memory: last 10 exchanges)
    messages = chat_history[-20:]  # 10 user+assistant pairs

    # Initial OpenAI API call
    response = await openai_client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    # Get assistant's response
    assistant_message = response.choices[0].message
    chat_history.append({"role": "assistant", "content": assistant_message.content or ""})

    # Handle tool calls if present
    if assistant_message.tool_calls:
        tool_messages = []
        for tool_call in assistant_message.tool_calls:
            result = await session.call_tool(
                tool_call.function.name,
                arguments=json.loads(tool_call.function.arguments),
            )
            tool_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result.content[0].text,
            })
        # Build a temporary message list for OpenAI: chat_history + assistant_message + tool_messages
        followup_messages = messages + [assistant_message] + tool_messages
        final_response = await openai_client.chat.completions.create(
            model=model,
            messages=followup_messages[-20:],
            tools=tools,
            tool_choice="none",
        )
        assistant_content = final_response.choices[0].message.content
        chat_history.append({"role": "assistant", "content": assistant_content or ""})
        return assistant_content

    return assistant_message.content


async def cleanup():
    """Clean up resources."""
    global exit_stack
    await exit_stack.aclose()


async def main():
    """
    Main entry point for the client. Runs an interactive chat loop with the user.
    """
    await connect_to_server("server.py")

    print("\nWelcome to the Azure OpenAI MCP Chat! Type 'exit' to quit.\n")
    try:
        while True:
            query = input("You: ").strip()
            if query.lower() in {"exit", "quit"}:
                print("Goodbye!")
                break
            if not query:
                continue
            response = await process_query(query)
            print(f"Assistant: {response}\n")
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main())