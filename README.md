# 🍕 Contoso Pizza AI Agent

An end-to-end intelligent pizza ordering agent built with Microsoft Azure AI Foundry, GPT-4o, and Model Context Protocol (MCP).

## 🎯 Project Overview

Built during the **Microsoft Azure OpenHack**, this project demonstrates how to build a production-ready AI agent that can hold natural conversations, retrieve knowledge, call custom functions, and interact with real backend systems via MCP.

## ✨ Features

- 🧠 **Persistent memory** — remembers customer name and order details across a conversation
- 📍 **Store knowledge (RAG)** — answers questions about 15 Contoso Pizza locations worldwide using vector search
- 🍕 **Pizza quantity calculator** — custom function tool that recommends how many pizzas to order based on group size
- 📦 **Real order management** — places, tracks, and cancels live orders via an MCP server
- 📊 **Live dashboard** — orders appear in real time on a web dashboard
- 😄 **Gen-alpha personality** — friendly, cheeky, and opinionated about pineapple on pizza

## 🏗️ Architecture

```
User
 │
 ▼
Azure AI Foundry Agent (GPT-4o)
 ├── File Search Tool ──────────► Vector Store (15 store .md files)
 ├── Function Tool ─────────────► calculate_pizza_quantity()
 └── MCP Tool ──────────────────► Pizza MCP Server
                                        │
                                        ▼
                                  Pizza API (Azure Functions)
                                        │
                                        ▼
                                  Live Dashboard
```

## 🛠️ Tech Stack

| Technology | Usage |
|---|---|
| Azure AI Foundry | Agent hosting and orchestration |
| GPT-4o | Language model |
| Model Context Protocol (MCP) | Real order placement and tracking |
| Azure Functions (Python) | Pizza quantity calculator API |
| Vector Store + File Search | RAG for store knowledge |
| OpenAI Responses API | Conversation and function calling |
| Python | Primary language |

## 📁 Project Structure

```
openhack-pizza/
├── 02_create_agent.py         # Level 2: Hello world agent
├── 03_add_instructions.py     # Level 3: Personality + persistent memory
├── 04_add_knowledge.py        # Level 4: Store knowledge via RAG
├── 05_function_calling.py     # Level 5: Pizza quantity function tool
├── 06_mcp.py                  # Level 6: MCP server integration
├── contoso-stores/            # Store knowledge files (15 locations)
├── old_version/               # Earlier iterations and experiments
│   ├── chat_test.py
│   ├── chat_with_agent.py
│   ├── create_agent_with_tools.py
│   ├── create_agent.py
│   ├── function_calling.py
│   └── mcp.py
├── .env                       # Environment variables
└── requirements.txt           # Python dependencies
```

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Azure subscription
- Azure AI Foundry project with GPT-4o deployed
- Azure CLI

### Installation

```bash
git clone https://github.com/yourusername/openhack-pizza
cd openhack-pizza
pip install -r requirements.txt
```

### Environment Setup

```bash
az login
```

### Run the Agent

```bash
python 06_mcp.py
```

## 💡 Key Learnings

- Debugging tool calls in agentic systems requires understanding the full request/response lifecycle
- MCP servers need `/sse` endpoint for proper Server-Sent Events connection
- The OpenAI Responses API requires function call outputs to be passed back via `input` not `tool_outputs`
- Reusing a single `conversation.id` is critical for persistent memory across turns
- `require_approval="never"` on `MCPTool` enables automatic tool execution without manual approval

## 📸 Demo

The agent can:
1. Greet customers and collect their name
2. Recommend pizza quantities for groups
3. Look up store locations and hours
4. Place real orders that appear on the live dashboard
5. Check order status and cancel if needed

## 🏆 Built At

**Microsoft Azure OpenHack** — AI Agents Track