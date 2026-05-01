from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Format: "https://resource_name.ai.azure.com/api/projects/project_name"
PROJECT_ENDPOINT = "https://michelle-openhack-pizza.services.ai.azure.com/api/projects/MichelleAnyanwu-OpenHack-Pizza"

# Create project and openai clients to call Foundry API
project = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)
openai = project.get_openai_client()

# Run a chat completions API call
response = openai.chat.completions.create(
    model="gpt-4o-openhack",
    messages=[{"role": "user", "content": "What is the size of France in square miles?"}]
)
print(f"Response: {response.choices[0].message.content}")