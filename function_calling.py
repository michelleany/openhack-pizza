import json
import math
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool, FileSearchTool
from azure.identity import DefaultAzureCredential

load_dotenv()

PROJECT_ENDPOINT = "https://michelle-openhack-pizza.services.ai.azure.com/api/projects/MichelleAnyanwu-OpenHack-Pizza"

stores_directory = (Path(__file__).parent / "./contoso-stores/").resolve()

project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

openai = project.get_openai_client()

# Simplified tool - just num_people, no appetite level
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

# Always create a new agent version
agent = project.agents.create_version(
    agent_name="MichelleOpenHackAgent",
    definition=PromptAgentDefinition(
        model="gpt-4o-openhack",
        instructions=(
            "You are a helpful pizza ordering assistant for Contoso Pizza. "
            "You have a Gen-alpha personality - friendly, helpful, and a bit cheeky. "
            "When a customer wants to order pizzas, ask how many people are attending. "
            "Then use the calculate_pizza_quantity function to determine how many pizzas to suggest. "
            "You can also provide store information and help customers choose toppings. "
            "You don't like pineapple on pizzas, but will help customers order it with some snark. "
            "Get the customer's name before placing an order. "
            "You can only help with pizza orders and Contoso Pizza information - politely deflect other topics."
        ),
        tools=[pizza_suggestion_tool, FileSearchTool(vector_store_ids=[vector_store.id])],
    ),
    description="Pizza ordering assistant with quantity recommendations.",
)
print(f"Agent created: {agent.name} (version: {agent.version})")

# Simple pizza calculation - 1 large pizza per 4 people
def calculate_pizza_quantity(num_people: int) -> str:
    pizzas_needed = math.ceil(num_people / 4)
    return json.dumps({
        "num_people": num_people,
        "pizzas_recommended": pizzas_needed,
        "message": f"{num_people} people → {pizzas_needed} large pizzas recommended"
    })

# Test conversation
conversation = openai.conversations.create()
test_query = "I'm throwing a party with 8 people. How many pizzas should I order?"
print(f"\n---\nQuery: {test_query}")

response = openai.responses.create(
    conversation=conversation.id,
    input=test_query,
    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
)

if hasattr(response, 'output_text') and response.output_text:
    print(f"Initial Response: {response.output_text}")

def has_function_calls(output):
    return isinstance(output, list) and any(
        getattr(item, 'type', None) == 'function_call' for item in output
    )

max_iterations = 10
iteration = 0

while has_function_calls(response.output) and iteration < max_iterations:
    iteration += 1
    tool_outputs = []

    for tool_call in response.output:
        if getattr(tool_call, 'type', None) == 'function_call':
            print(f"Function Call: {tool_call.name}")
            args = json.loads(tool_call.arguments)
            result = calculate_pizza_quantity(num_people=args["num_people"])
            result_data = json.loads(result)
            print(f"✓ Pizzas recommended: {result_data['pizzas_recommended']}")
            tool_outputs.append({
                "tool_call_id": tool_call.call_id,
                "output": result
            })

    response = openai.responses.create(
        conversation=conversation.id,
        input=[
            {
                "type": "function_call_output",
                "call_id": to["tool_call_id"],
                "output": to["output"]
            }
            for to in tool_outputs
        ],
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )

    if hasattr(response, 'output_text') and response.output_text:
        print(f"Agent Response: {response.output_text}")
    elif isinstance(response.output, list):
        for item in response.output:
            if hasattr(item, 'text') and item.text:
                print(f"Agent Response: {item.text}")
