import json
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, Tool, FunctionTool, FileSearchTool
from azure.identity import DefaultAzureCredential
from openai.types.responses.response_input_param import FunctionCallOutput, ResponseInputParam

# Load environment variables from .env file
load_dotenv()

# Format: "https://resource_name.ai.azure.com/api/projects/project_name"
PROJECT_ENDPOINT = "https://michelle-openhack-pizza.services.ai.azure.com/api/projects/MichelleAnyanwu-OpenHack-Pizza"
AGENT_NAME = "MichelleOpenHackAgent"

# Load the file to be indexed for search.
stores_directory = (Path(__file__).parent / "./contoso-stores/").resolve()

# Create project client to call Foundry API
project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

openai = project.get_openai_client()

# Define a function tool for pizza quantity suggestions
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
            "appetite_level": {
                "type": "string",
                "enum": ["light", "moderate", "heavy"],
                "description": "The appetite level of the group (light, moderate, or heavy)",
            },
        },
        "required": ["num_people", "appetite_level"],
        "additionalProperties": False,
    },
    description="Calculate the recommended number of pizzas based on party size and appetite level.",
    strict=True,
)

tools: list[Tool] = [pizza_suggestion_tool]

vector_store = openai.vector_stores.create(name="ContosoStoresInfo")
    
# Upload ALL store files to the vector store for RAG retrieval
store_files = list(stores_directory.glob("*.md"))
print(f"Uploading {len(store_files)} store files to vector store for RAG...")
    
for file_path in store_files:
    if file_path.exists():
        with open(file_path, "rb") as file_handle:
            openai.vector_stores.files.upload_and_poll(
                vector_store_id=vector_store.id,
                file=file_handle,
            )
        print(f"  ✓ Uploaded: {file_path.name}")

# Try to retrieve existing vector store, or create if it doesn't exist
"""try:
    # List vector stores and find one with matching name
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
    print("Vector store not found, creating new vector store...")
    vector_store = openai.vector_stores.create(name="ContosoStoresInfo")
    
    # Upload ALL store files to the vector store for RAG retrieval
    store_files = list(stores_directory.glob("*.md"))
    print(f"Uploading {len(store_files)} store files to vector store for RAG...")
    
    for file_path in store_files:
        if file_path.exists():
            with open(file_path, "rb") as file_handle:
                openai.vector_stores.files.upload_and_poll(
                    vector_store_id=vector_store.id,
                    file=file_handle,
                )
            print(f"  ✓ Uploaded: {file_path.name}")
"""

agent = project.agents.create_version(
    agent_name="MichelleOpenHackAgent",
    definition=PromptAgentDefinition(
        model="gpt-4o-openhack",
        instructions=(
                "You are a helpful pizza ordering assistant for Contoso Pizza. You have a Gen-alpha personality - friendly, helpful, and a bit cheeky. When a customer wants to order pizzas, you MUST ask for the following information BEFORE making any suggestions: 1. Number of people attending 2. Their appetite level (light, moderate, or heavy) Once you have this information, use the calculate_pizza_quantity function to determine how many pizzas to suggest. If the function is unavailable, calculate it yourself using these exact formulas: Light appetite: max(1, num_people divided by 4, rounded down). Moderate appetite: max(1, num_people plus 1 divided by 2, rounded down). Heavy appetite: max(1, num_people multiplied by 2 plus 1, divided by 3, rounded down). Always state the exact number of pizzas calculated. Then provide a recommendation with explanation. You can also provide store information and help customers choose toppings. You don't like pineapple on pizzas, but will help customers order it with some snark. Get the customer's name before placing an order. You can only help with pizza orders and Contoso Pizza information - politely deflect other topics."
        ),
        tools=[FileSearchTool(vector_store_ids=[vector_store.id])],
        #tools=[pizza_suggestion_tool, FileSearchTool(vector_store_ids=[vector_store.id])],
    ),
    description="Pizza ordering assistant with quantity recommendations.",
)
print(f"Agent created: {agent.name} (version: {agent.version})\n\n")

# Try to retrieve existing agent, or create if it doesn't exist
"""try:
    agent = project.agents.get("MichelleOpenHackAgent")
    print(f"Retrieved existing agent: {agent.name} (version: {agent.version})")
except Exception:
    print("Agent not found, creating new agent...")
    agent = project.agents.create_version(
        agent_name="MichelleOpenHackAgent",
        definition=PromptAgentDefinition(
            model="gpt-4o-openhack",
            instructions=(
                "You are a helpful pizza ordering assistant for Contoso Pizza. "
                "You have a Gen-alpha personality - friendly, helpful, and a bit cheeky. "
                "When a customer wants to order pizzas, you MUST ask for the following information BEFORE making any suggestions: "
                "1. Number of people attending "
                "2. Their appetite level (light, moderate, or heavy) "
                "Once you have this information, use the calculate_pizza_quantity function to determine how many pizzas to suggest. "
                "Then provide a recommendation with explanation. "
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
"""
# Test conversation with pizza ordering
conversation = openai.conversations.create()

# Example interaction
test_query = "I'm throwing a party with 8 people who all have a heavy appetite. How many pizzas should I order?"
print(f"\n---\nQuery: {test_query}")

def calculate_pizza_quantity(num_people: int, appetite_level: str) -> str:
    """
    Calculate recommended number of pizzas based on party size and appetite.
    
    Pizza calculation logic:
    - Light appetite: 1 pizza per 3-4 people
    - Moderate appetite: 1 pizza per 2-3 people
    - Heavy appetite: 1 pizza per 1.5-2 people
    """
    if appetite_level == "light":
        pizzas_needed = max(1, num_people // 4)
    elif appetite_level == "moderate":
        pizzas_needed = max(1, (num_people + 1) // 2)
    else:  # heavy
        pizzas_needed = max(1, (num_people * 2 + 1) // 3)
    
    suggestions = {
        "light": f"{num_people} people with light appetite → {pizzas_needed} pizzas recommended",
        "moderate": f"{num_people} people with moderate appetite → {pizzas_needed} pizzas recommended",
        "heavy": f"{num_people} people with heavy appetite → {pizzas_needed} pizzas recommended"
    }
    
    return json.dumps({
        "num_people": num_people,
        "appetite_level": appetite_level,
        "pizzas_recommended": pizzas_needed,
        "message": suggestions[appetite_level]
    })

# Handle the conversation with tool calls
response = openai.responses.create(
    conversation=conversation.id,
    input=test_query,
    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
)

# troubleshooting
# print(f"Response status: {response.status}")
# print(f"Response output type: {type(response.output)}")


# Try to get the response text
if hasattr(response, 'output_text'):
    print(f"Initial Response: {response.output_text}")
elif hasattr(response, 'output'):
    if isinstance(response.output, list):
        for item in response.output:
            if hasattr(item, 'text'):
                print(f"Response: {item.text}")
    else:
        print(f"Response: {response.output}")
else:
    print(f"Full response object: {response}")

# Process function calls if the agent made any
max_iterations = 10
iteration = 0

# Handle the conversation with tool calls - check for function calls regardless of status
def has_function_calls(output):
    return isinstance(output, list) and any(
        getattr(item, 'type', None) == 'function_call' for item in output
    )

while has_function_calls(response.output) and iteration < max_iterations:
    iteration += 1
    print(f"\n--- Iteration {iteration} ---")
    
    tool_outputs = []
    
    for tool_call in response.output:
        if getattr(tool_call, 'type', None) == 'function_call':
            print(f"Function Call: {tool_call.name}")
            print(f"Arguments: {tool_call.arguments}")
            
            if tool_call.name == "calculate_pizza_quantity":
                args = json.loads(tool_call.arguments)
                result = calculate_pizza_quantity(
                    num_people=args["num_people"],
                    appetite_level=args["appetite_level"]
                )
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
    
    print(f"New response status: {response.status}")
    if hasattr(response, 'output_text') and response.output_text:
        print(f"Agent Response: {response.output_text}")
    elif isinstance(response.output, list):
        for item in response.output:
            if hasattr(item, 'text') and item.text:
                print(f"Agent Response: {item.text}")