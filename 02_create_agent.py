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

# Create a simple hello agent
agent = project.agents.create_version(
    agent_name="MichelleOpenHackAgent",
    definition=PromptAgentDefinition(
        model="gpt-4o",
        instructions="You are a friendly assistant. Always respond with 'Hello' to any input.",
    ),
    description="A simple hello agent.",
)
print(f"Agent created: {agent.name} (version: {agent.version})")

# Test conversation
conversation = openai.conversations.create()

response = openai.responses.create(
    conversation=conversation.id,
    input="Hi there!",
    extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
)

if hasattr(response, 'output_text') and response.output_text:
    print(f"Agent Response: {response.output_text}")
elif isinstance(response.output, list):
    for item in response.output:
        if hasattr(item, 'text') and item.text:
            print(f"Agent Response: {item.text}")

print("\n✓ Hello agent working!")