from pathlib import Path

from dotenv import load_dotenv
import os
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FileSearchTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential

# Load environment variables from .env file
load_dotenv()

# Format: "https://resource_name.ai.azure.com/api/projects/project_name"
PROJECT_ENDPOINT = os.getenv("PROJECT_ENDPOINT", "https://michelle-openhack-pizza.services.ai.azure.com/api/projects/MichelleAnyanwu-OpenHack-Pizza")
AGENT_NAME = os.getenv("AZURE_AI_FOUNDRY_AGENT_NAME", "MichelleOpenHackAgent")

# Load the file to be indexed for search.
stores_directory = (Path(__file__).parent / "./contoso-stores/").resolve()

# Create project client to call Foundry API
project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

openai = project.get_openai_client()
# The openai client uses {PROJECT_ENDPOINT}/openai/v1 for file and vector store operations

# Create vector store for RAG
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

# Try to retrieve existing agent, or create if it doesn't exist
try:
    agent = project.agents.get("MichelleOpenHackAgent")
    print(f"Retrieved existing agent: {agent.name} (version: {agent.version})")
except Exception:
    print("Agent not found, creating new agent...")
    agent = project.agents.create_version(
        agent_name="MichelleOpenHackAgent",
        definition=PromptAgentDefinition(
            model="gpt-4o-openhack",
            instructions=(
                "You are a helpful agent that searches through Contoso Pizza store information. "
                "Use the file search tool to find relevant information from store files to answer user questions. "
                "The file search will automatically retrieve the most relevant store information based on the user's query. "
                "Provide accurate and helpful responses based on the retrieved information."
                "You will ask for a store location from the user, then use the file search tool to find information about that store, and then answer the user's question based on the retrieved information."
                "You are an agent that helps customers order pizzas from Contoso pizza. You have a Gen-alpha personality, so you are friendly and helpful, but also a bit cheeky. You can provide information about Contoso Pizza and its retail stores. You help customers order a pizza of their chosen size, crust, and toppings. You don't like pineapple on pizzas, but you will help a customer a pizza with pineapple ... with some snark. Make sure you know the customer's name before placing an order on their behalf. You can't do anything except help customers order pizzas and give information about Contoso Pizza. You will gently deflect any other questions."
            ),
            tools=[FileSearchTool(vector_store_ids=[vector_store.id])],
        ),
        description="RAG-enabled agent for Contoso Pizza store information queries.",
    )
    print(f"Agent created: {agent.name} (version: {agent.version})")

# Example queries to test RAG retrieval
queries = [
    "Tell me about the Boston store",
    "What's available at the Amsterdam location?",
    "Show me Chicago pizza options",
]

# Create conversation for multi-turn chat
conversation = openai.conversations.create()

for user_query in queries:
    print(f"\n---\nQuery: {user_query}")
    
    response = openai.responses.create(
        conversation=conversation.id,
        input=user_query,
        extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
    )
    print(f"Response: {response.output_text}")
