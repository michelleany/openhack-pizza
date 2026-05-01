from pathlib import Path
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FileSearchTool
from azure.identity import DefaultAzureCredential

load_dotenv()

PROJECT_ENDPOINT = "https://openhack.services.ai.azure.com/api/projects/michelle-openhack-pizza"
AGENT_NAME = "MichellePizzaAgent-Level4"
stores_directory = (Path(__file__).parent / "contoso-stores/").resolve()

project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

openai = project.get_openai_client()

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
        raise Exception("not found")
except Exception:
    print("Creating new vector store...")
    vector_store = openai.vector_stores.create(name="ContosoStoresInfo")
    store_files = list(stores_directory.glob("*.md"))
    print(f"Uploading {len(store_files)} store files...")
    for file_path in store_files:
        with open(file_path, "rb") as f:
            openai.vector_stores.files.upload_and_poll(
                vector_store_id=vector_store.id, file=f
            )
        print(f"  ✓ Uploaded: {file_path.name}")

# Delete existing agent with same name
try:
    project.agents.delete(AGENT_NAME)
    print(f"Deleted existing agent: {AGENT_NAME}")
except Exception:
    pass

# Create agent with file search
agent = project.agents.create_version(
    agent_name=AGENT_NAME,
    definition=PromptAgentDefinition(
        model="gpt-4o",
        instructions=(
            "You are an agent that helps customers order pizzas from Contoso Pizza. "
            "You have a Gen-alpha personality, so you are friendly and helpful, but also a bit cheeky. "
            "You can provide information about Contoso Pizza and its retail stores. "
            "You help customers order a pizza of their chosen size, crust, and toppings. "
            "You don't like pineapple on pizzas, but you will help a customer order a pizza with pineapple... with some snark. "
            "Make sure you know the customer's name before placing an order on their behalf. "
            "Always ask which store location the customer wants to order from before confirming any order. "
            "Use your store knowledge to list available locations and answer questions about them. "
            "You can't do anything except help customers order pizzas and give information about Contoso Pizza. "
            "Politely deflect any non-pizza-related questions."
        ),
        tools=[FileSearchTool(vector_store_ids=[vector_store.id])],
    ),
    description="Level 4 pizza agent with store knowledge.",
)
print(f"Agent created: {agent.name} (version: {agent.version})")

# Single conversation for persistent memory
conversation = openai.conversations.create()
print(f"\nChat with your pizza agent! Type 'quit' to exit.\n")

while True:
    user_input = input("You: ").strip()
    if user_input.lower() == "quit":
        break

    response = openai.responses.create(
        conversation=conversation.id,
        input=user_input,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )

    if hasattr(response, 'output_text') and response.output_text:
        print(f"Agent: {response.output_text}\n")
    elif isinstance(response.output, list):
        for item in response.output:
            if hasattr(item, 'text') and item.text:
                print(f"Agent: {item.text}\n")