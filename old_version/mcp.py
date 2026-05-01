import json
import math
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool, FileSearchTool, MCPTool
from azure.identity import DefaultAzureCredential

load_dotenv()

PROJECT_ENDPOINT = "https://michelle-openhack-pizza.services.ai.azure.com/api/projects/MichelleAnyanwu-OpenHack-Pizza"

stores_directory = (Path(__file__).parent / "./contoso-stores/").resolve()

project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

openai = project.get_openai_client()

USER_ID = "c6e01d6d-2475-482e-b230-e74aaf8d4ed4"
MCP_SERVER_URL = "https://ca-pizza-mcp-i77g52gdb73be.calmsmoke-e2439346.westus3.azurecontainerapps.io/"

# Simple pizza calculation tool
pizza_suggestion_tool = FunctionTool(
    name="calculate_pizza_quantity",
    parameters={
        "type": "object",
        "properties": {
            "num_people": {
                "type": "integer",
                "description": "Number of people attending the pizza party",
                "minimum": 1,
            },
        },
        "required": ["num_people"],
        "additionalProperties": False,
    },
    description="Calculate the recommended number of pizzas. A large pizza serves 4 people.",
    strict=True,
)

# Vector store - retrieve existing or create new
try:
    vector_stores = openai.vector_stores.list()
    vector_store = None
    for vs in vector_stores.data:
        if vs.name == "ContosoStoresInfo":
            vector_store = vs
            print(f"Retrieved existing vector store: {vector_store.name} (id: {vector_store.id})")
            break
    if vector_store is None:
        raise Exception("Vector store not found")
except Exception:
    print("Creating new vector store...")
    vector_store = openai.vector_stores.create(name="ContosoStoresInfo")
    store_files = list(stores_directory.glob("*.md"))
    for file_path in store_files:
        if file_path.exists():
            with open(file_path, "rb") as f:
                openai.vector_stores.files.upload_and_poll(
                    vector_store_id=vector_store.id, file=f
                )
            print(f"  ✓ Uploaded: {file_path.name}")

# MCP Tool connection
mcp_tool = MCPTool(
    server_label="contoso_pizza",
    server_url=MCP_SERVER_URL,
    allowed_tools=[],  # empty = allow all tools from MCP server
)

# Create new agent version with MCP
agent = project.agents.create_version(
    agent_name="MichelleOpenHackAgent",
    definition=PromptAgentDefinition(
        model="gpt-4o-openhack",
        instructions=(
            f"You are a helpful pizza ordering assistant for Contoso Pizza. "
            f"You have a Gen-alpha personality - friendly, helpful, and a bit cheeky. "
            f"The current user's ID is: {USER_ID}. Always use this ID when placing or managing orders. "
            f"When a customer wants to order pizzas, ask how many people are attending, then use "
            f"the calculate_pizza_quantity function to determine how many pizzas to suggest. "
            f"Use the MCP tools to place, track, and cancel orders. "
            f"Guide the user through the full ordering process step by step. "
            f"You can also provide store information and help customers choose toppings. "
            f"You don't like pineapple on pizzas, but will help customers order it with some snark. "
            f"Get the customer's name before placing an order. "
            f"You can only help with pizza orders and Contoso Pizza information - politely deflect other topics."
        ),
        tools=[pizza_suggestion_tool, FileSearchTool(vector_store_ids=[vector_store.id]), mcp_tool],
    ),
    description="Pizza ordering assistant with MCP integration.",
)
print(f"Agent created: {agent.name} (version: {agent.version})")