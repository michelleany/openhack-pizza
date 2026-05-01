import json
import math
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool, FileSearchTool
from azure.identity import DefaultAzureCredential
import time

load_dotenv()

PROJECT_ENDPOINT = "https://openhack.services.ai.azure.com/api/projects/michelle-openhack-pizza"
AGENT_NAME = "MichellePizzaAgent-Level5"
stores_directory = (Path(__file__).parent / "contoso-stores/").resolve()

project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)
openai = project.get_openai_client()

# Pizza calculation function
def calculate_pizza_quantity(num_people: int) -> str:
    pizzas_needed = math.ceil(num_people / 4)
    return json.dumps({
        "num_people": num_people,
        "pizzas_recommended": pizzas_needed,
        "message": f"{num_people} people → {pizzas_needed} large pizzas recommended"
    })

# Function tool definition
pizza_suggestion_tool = FunctionTool(
    name="calculate_pizza_quantity",
    parameters={
        "type": "object",
        "properties": {
            "num_people": {
                "type": "integer",
                "description": "Number of people attending",
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
            print(f"Retrieved existing vector store: {vector_store.name}")
            break
    if vector_store is None:
        raise Exception("not found")
except Exception:
    print("Creating new vector store...")
    vector_store = openai.vector_stores.create(name="ContosoStoresInfo")
    store_files = list(stores_directory.glob("*.md"))
    for file_path in store_files:
        with open(file_path, "rb") as f:
            openai.vector_stores.files.upload_and_poll(
                vector_store_id=vector_store.id, file=f
            )
        print(f"  ✓ Uploaded: {file_path.name}")

# Create agent
agent = project.agents.create_version(
    agent_name=AGENT_NAME,
    definition=PromptAgentDefinition(
        model="gpt-4o",
        instructions=(
            "You are an agent that helps customers order pizzas from Contoso Pizza. "
            "You have a Gen-alpha personality, so you are friendly and helpful, but also a bit cheeky. "
            "When a customer wants to order pizzas, ask how many people are attending, then use "
            "the calculate_pizza_quantity function to suggest how many pizzas to order. "
            "Always ask which store location the customer wants to order from before confirming any order. "
            "Make sure you know the customer's name before placing an order. "
            "You can also provide store information and help customers choose toppings. "
            "You don't like pineapple on pizzas, but will help customers order it with some snark. "
            "You can only help with pizza orders and Contoso Pizza information - politely deflect other topics."
        ),
        tools=[pizza_suggestion_tool, FileSearchTool(vector_store_ids=[vector_store.id])],
    ),
    description="Level 5 pizza agent with estimation function.",
)
print(f"Agent created: {agent.name} (version: {agent.version})")

# Helper with retry
def call_with_retry(fn, max_retries=3):
    for i in range(max_retries):
        try:
            return fn()
        except Exception as e:
            if "too_many_requests" in str(e).lower():
                wait = 2 ** i
                print(f"Rate limited, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise Exception("Max retries exceeded")

# Helper to handle function calls
def has_function_calls(output):
    return isinstance(output, list) and any(
        getattr(item, 'type', None) == 'function_call' for item in output
    )

def process_response(response):
    max_iterations = 10
    iteration = 0

    while has_function_calls(response.output) and iteration < max_iterations:
        iteration += 1
        tool_outputs = []

        for tool_call in response.output:
            if getattr(tool_call, 'type', None) == 'function_call':
                if tool_call.name == "calculate_pizza_quantity":
                    args = json.loads(tool_call.arguments)
                    result = calculate_pizza_quantity(num_people=args["num_people"])
                    tool_outputs.append({
                        "tool_call_id": tool_call.call_id,
                        "output": result
                    })

        response = call_with_retry(lambda: openai.responses.create(
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
        ))

    # Print final response
    if hasattr(response, 'output_text') and response.output_text:
        print(f"Agent: {response.output_text}\n")
    elif isinstance(response.output, list):
        for item in response.output:
            if hasattr(item, 'text') and item.text:
                print(f"Agent: {item.text}\n")

# Single conversation for persistent memory
conversation = openai.conversations.create()
print(f"\nChat with your pizza agent! Type 'quit' to exit.\n")

while True:
    user_input = input("You: ").strip()
    if user_input.lower() == "quit":
        break

    response = call_with_retry(lambda: openai.responses.create(
        conversation=conversation.id,
        input=user_input,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    ))

    process_response(response)