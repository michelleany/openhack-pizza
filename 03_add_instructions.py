from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential

load_dotenv()

PROJECT_ENDPOINT = "https://openhack.services.ai.azure.com/api/projects/michelle-openhack-pizza"

project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)

openai = project.get_openai_client()

AGENT_NAME = "MichellePizzaAgent-Level3"

# Delete existing agent with same name to keep things clean
try:
    existing = project.agents.get(AGENT_NAME)
    project.agents.delete(AGENT_NAME)
    print(f"Deleted existing agent: {AGENT_NAME}")
except Exception:
    pass

# Create pizza agent with personality
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
            "You can't do anything except help customers order pizzas and give information about Contoso Pizza. "
            "Politely deflect any non-pizza-related questions."
        ),
    ),
    description="Level 3 pizza agent with personality and persistent memory.",
)
print(f"Agent created: {agent.name} (version: {agent.version})")

# Create a SINGLE conversation - reuse it to maintain memory
conversation = openai.conversations.create()
print(f"Conversation created: {conversation.id}")
print("\nChat with your pizza agent! Type 'quit' to exit.\n")

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