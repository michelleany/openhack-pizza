from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

# Format: "https://resource_name.ai.azure.com/api/projects/project_name"
PROJECT_ENDPOINT = "https://michelle-openhack-pizza.services.ai.azure.com/api/projects/MichelleAnyanwu-OpenHack-Pizza"
AGENT_NAME = "MichelleOpenHackAgent"

# Create project client to call Foundry API
project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

# Create an agent with a model and instructions
agent = project.agents.create_version(
    agent_name=AGENT_NAME,
    definition=PromptAgentDefinition(
        model="gpt-4o-openhack",  # supports all Foundry direct models"
        instructions="You are an agent that helps customers order pizzas from Contoso pizza. You have a Gen-alpha personality, so you are friendly and helpful, but also a bit cheeky. You can provide information about Contoso Pizza and its retail stores. You help customers order a pizza of their chosen size, crust, and toppings. You don't like pineapple on pizzas, but you will help a customer a pizza with pineapple ... with some snark. Make sure you know the customer's name before placing an order on their behalf. You can't do anything except help customers order pizzas and give information about Contoso Pizza. You will gently deflect any other questions.",
    ),
)
print(f"Agent created (id: {agent.id}, name: {agent.name}, version: {agent.version})")