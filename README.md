# Agent Development Toolkit (ADT) For Strands Documentation

**A development tool for building AI agents with the Strands platform**

ADT provides a single command-line interface that lets developers build, test, and iterate on Strands agents with the same ease as modern web frameworks. The CLI unifies agent execution, observability, UI, and containerization into one cohesive developer experience.

---

## Table of Contents

1. [What is ADT?](#what-is-adt)
2. [Quick Start](#quick-start)
3. [Installation](#installation)
4. [Core Commands](#core-commands)
5. [Creating Your First Agent](#creating-your-first-agent)
6. [Development Workflow](#development-workflow)
7. [Project Structure](#project-structure)
8. [Configuration](#configuration)
9. [Adding Custom Tools](#adding-custom-tools)
10. [Built-in Tools](#built-in-tools)
11. [Model Context Protocol (MCP) Integration](#model-context-protocol-mcp-integration)
12. [UI and Observability](#ui-and-observability)
13. [Docker and Container Mode](#docker-and-container-mode)
14. [Advanced Features](#advanced-features)
15. [Troubleshooting](#troubleshooting)
16. [Reference](#reference)

---

## What is ADT?

ADT (Agent Development Toolkit) is a development tool that works with the [Strands platform](https://strandsagents.com/latest/). It provides:

- **Project scaffolding** - Generates agent project structure with configuration files
- **Development server** - Runs agents locally with a FastAPI backend
- **Chat interface** - Web UI for interacting with agents during development
- **Tool integration** - Supports custom tools and MCP protocol
- **Container support** - Can run the development server in Docker

### What it does:

- Generates complete agent project directories
- Provides templates for agent configuration and tool development  
- Runs a local web server with chat interface to test agent locally
- Auto-discovers tools in the project for custom tool via tools directory
- Integrates with Model Context Protocol servers




## Quick Start

```bash
# Install ADT
pip install git+https://github.com/awslabs/agent-dev-toolkit.git

# Create an agent project
adt init my-agent
cd my-agent

# Start the development server
adt dev --port 8083
```

Agent chat playground will be available at http://localhost:8083.

---

## Installation

### Prerequisites

**Required:**
- Python 3.10 or higher
- pip (Python package manager)
- Node.js 18+ - Required for UI assets

**Optional:**
- Docker - For container mode

### Install ADT

**Option 1: From GitLab (Recommended)**
```bash
pip install git+https://github.com/awslabs/agent-dev-toolkit.git
```

**Option 2: Clone repo**
```bash
git clone https://github.com/awslabs/agent-dev-toolkit.git
cd agent-dev-toolkit
pip install -e .
```

### Verify Installation

```bash
adt --help
```

---

## Core Commands

| Command | Function |
|---------|----------|
| `adt init <project-name>` | Generate a new agent project directory |
| `adt dev` | Start development server with chat UI |
| `adt add tool <tool-name>` | Generate a tool stub file in tools directory |

### Command Options

**`adt init`**
- No additional options

**`adt dev`**
- `--port, -p` - Server port (default: 8000)
- `--container` - Run backend in Docker container
- `--env-file` - Load environment variables from file
- `--aws-profile` - Use specific AWS credentials profile

---

## Creating Your First Agent

### Step 1: Generate Project

```bash
adt init my-agent
cd my-agent
```

This creates:
- `.agent.yaml` - Agent configuration file
- `src/agent.py` - Main agent implementation
- `src/tools/` - Directory for custom tools
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container configuration
- `container_entrypoint.py` - Container server script

### Step 2: Configure Agent

Edit `.agent.yaml`:

```yaml
name: my-agent
system_prompt: "You are a helpful AI assistant."

provider:
  class: "strands.models.BedrockModel"
  kwargs:
    model_id: "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    region_name: "us-west-2"
    temperature: 0.7
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Start Development Server

```bash
adt dev --port 8083
```

The UI will build automatically on first run and be available at http://localhost:8083.

---

## Development Workflow

### Local Development

```bash
adt dev --port 8083
```
- Runs agent backend locally
- Serves built UI assets
- UI builds automatically on first run

### Container Mode

Run the backend in a Docker container:
```bash
adt dev --container --port 9000
```
- Backend runs in Docker container
- UI runs locally and connects to container
- Useful for experimenting with containerized environments

### Environment Management
> Examples

Load environment variables:
```bash
adt dev --env-file .env
```

Use AWS profile:
```bash
adt dev --aws-profile dev-profile
```

Use environment variables
```
export AWS_ACCESS_KEY_ID=<>
export AWS_SECRET_ACCESS_KEY=<>

adt dev --port 8083
```

---

## Project Structure

Generated project structure:

```
my-assistant/
├── src/
│   ├── agent.py              # Agent implementation
│   ├── tools/                # Custom tools
│   │   ├── __init__.py       # Tool auto-discovery
│   │   └── sample_tool.py    # Example tool
│   ├── mcp_client.py         # MCP integration helper
│   └── mcp_tools.py          # MCP tool loader
├── .agent.yaml               # Agent configuration
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies  
├── Dockerfile                # Container configuration
├── container_entrypoint.py   # Container server
└── README.md                 # Project documentation
```

### Key Files

**`.agent.yaml`** - Agent configuration including model provider and system prompt

**`src/agent.py`** - Main agent implementation that loads configuration

**`src/tools/`** - Directory for custom tool development with automatic discovery

**`container_entrypoint.py`** - FastAPI server for container mode

---

## Configuration

### Agent Configuration (`.agent.yaml`)

Example configuration:

```yaml
name: customer-support-bot
system_prompt: |
  You are a helpful customer support assistant.

provider:
  class: "strands.models.BedrockModel"
  kwargs:
    model_id: "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    region_name: "us-west-2"
    temperature: 0.3
    max_tokens: 2048

# Optional: MCP server integrations
mcp_servers:
  - name: aws_documentation
    transport: stdio
    command: ["uvx", "awslabs.aws-documentation-mcp-server@latest"]
```

### Provider Configuration

**AWS Bedrock:**
```yaml
provider:
  class: "strands.models.BedrockModel"
  kwargs:
    model_id: "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    region_name: "us-west-2"
    temperature: 0.7
```

**Environment Variable References:**
Configuration keys ending with `_env` are resolved from environment variables:
```yaml
provider:
  kwargs:
    api_key_env: ANTHROPIC_API_KEY  # Reads from $ANTHROPIC_API_KEY
```
> Please refer to Model Providers section of Strands documentation for more info https://strandsagents.com/latest/


### Environment Variables

Create `.env` file:
```bash
# If using Bedrock as model provider set AWS Credentials 
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-west-2

# OR

# API Keys for other Model Providers
ANTHROPIC_API_KEY=your_api_key
```
> env file can be passed to ```adt dev``` command using --env-file option
---

## Adding Custom Tools

Tools are functions that agents can call during conversations.

### Generate Tool Template

```bash
adt add tool weather_checker
```

This creates `src/tools/weather_checker.py`:

```python
from strands import tool

@tool
def weather_checker(location: str) -> str:
    """Check the weather for a given location.
    
    Args:
        location: The city or location to check weather for
        
    Returns:
        str: Weather information for the location
    """
    # Implement weather checking functionality
    return f"Weather checker called for: {location}"
```



### Tool Auto-Discovery

Tools placed in `src/tools/` are automatically discovered through the `__init__.py` file. No manual registration required. If you don't want the tools to be auto discovered, you can disable it by commenting out ```tools.extend(get_tools())``` in ```create_agent()``` method.

---

## Built-in Tools

The [strands-agents-tools](https://github.com/strands-agents/tools) library provides pre-built tools. Please check the documentation for a list of available tools.

### Enabling Built-in Tools

> Tools from [strands-agents-tools](https://github.com/strands-agents/tools) can be made available to your agent by importing and passing them to your agent.

Edit `src/agent.py`:

```python
# Uncomment these imports
from strands_tools import calculator, web_search, file_read

def create_agent():
    # ... existing code ...
    
    # Uncomment this line to add built-in tools
    tools.extend([calculator, web_search, file_read])
    
    return agent
```

Restart the development server:
```bash
adt dev
```

---

## Model Context Protocol (MCP) Integration

MCP allows agents to connect to external services through a standardized protocol. For more details on MCP, refer to https://github.com/modelcontextprotocol


### Setting Up MCP

**1. Install MCP dependencies:**
> In your agent project environment, install the mcp dependencies. If you are using a virtual environment, activate it before installing mcp package.
```bash
pip install mcp           # MCP protocol client
pip install uv            # For uvx-based servers (optional)
```

**2. Configure MCP servers in `.agent.yaml`:**

> Please check .agent.yaml file in your project for examples of mcp server configurations. ADT supports stdio and streamable_http transports

```yaml
mcp_servers:
  - name: aws_documentation
    transport: stdio
    command: ["uvx", "awslabs.aws-documentation-mcp-server@latest"]
```

**3. Enable MCP in agent:**

Edit `src/agent.py`:
```python
from src.mcp_tools import get_mcp_tools_sync

def create_agent():
    # ... existing code ...
    
    # Uncomment this line to enable MCP
    tools.extend(get_mcp_tools_sync(cfg.get("mcp_servers", [])))
    
    return agent
```

### Supported MCP Transport Types

**stdio transport** - For command-line MCP servers:
```yaml
- name: file_server
  transport: stdio
  command: ["uvx", "mcp-server-files@latest"]
```

**Streamable HTTP transport** 
```yaml
- name: simple_test_server
  transport: streamable_http
  url: "http://localhost:8002/mcp"
  headers:
    User-Agent: "TestAgent/1.0"
```

---

## UI and Observability

### Chat Interface

The chat interface is built into the CLI and provides a simple UI to interact with the agent.

### Observability Features

**Message inspection** - Click "View Trace" button to view:
- Execution timeline and agent reasoning steps
- Token usage for input and output
- Tool calls and their results
- Response times and performance data

**Sequence diagrams** - Visual representation of:
- Agent and tool interactions
- Multi-step reasoning flows


---

## Docker and Container Mode

### Container Mode

Run the backend in a Docker container:
```bash
adt dev --container --port 9000
```

This will:
- Build a Docker image with the agent
- Run backend in the container
- Serve UI locally, connecting to the containerized backend

### ⚠️ Important: Provider Dependencies

**Container mode requires all provider dependencies to be listed in `requirements.txt`.**

The container builds from your `requirements.txt` file, so you must include the appropriate packages for your configured provider:

```txt
# requirements.txt
strands-agents>=1.0.0
# Add provider-specific packages here based on your .agent.yaml configuration
# Check your provider's documentation for required dependencies
# ... other dependencies
```

### Container Rebuild Required

When you add new dependencies to `requirements.txt`, you must rebuild the container:

```bash
# After updating requirements.txt
adt dev --container --rebuild --port 9000
```

The `--rebuild` flag forces a fresh Docker build that includes your updated dependencies.

### Container Configuration

The generated `Dockerfile` includes:
- Python 3.11 slim base image
- FastAPI and Uvicorn installation
- Automatic installation of your `requirements.txt` dependencies
- Health check endpoint
- Environment variable support

> Please note: The DOCKERFILE created as part of project scaffolding is intended for local testing only.

### Provider Environment Variables

```bash
adt dev --container --env-file .provider_env
```
```env
# .provider_env
PROVIDER_API_KEY=your_api_key
# Add other provider-specific environment variables as needed
```

---

## Troubleshooting

### Common Issues

**❌ "Node.js not found. Cannot build UI assets."**
```
❌ Node.js not found. Cannot build UI assets.
   Please install Node.js ≥18 from https://nodejs.org/
   Then run: adt dev
```
**Solution:** Install Node.js ≥18 from [nodejs.org](https://nodejs.org/)

**❌ "UI build failed"**
```
❌ UI build failed.
   Check that Node.js ≥18 is installed and try again.
```
**Solutions:**
1. Check Node.js version: `node --version`
2. Clear npm cache: `npm cache clean --force`  
3. Manual build: `adt build-ui`

**❌ "Agent file not found"**
```
❌ Agent file not found: /path/to/src/agent.py
```
**Solution:** Run `adt dev` from the project directory

**❌ "Missing dependency"**
```
❌ Missing dependency 'strands-agents' and no requirements.txt found.
```
**Solution:** Install dependencies: `pip install -r requirements.txt`

**❌ "Container mode fails with missing provider dependencies"**
```
ModuleNotFoundError: No module named '[provider_package]'
Backend error: Expecting value: line 1 column 1 (char 0)
```
**Solutions:**
1. Add provider-specific dependencies to `requirements.txt` based on your configured provider
2. Rebuild the container: `adt dev --container --rebuild`
3. Check container logs: `docker logs $(docker ps -q --filter ancestor=agent:latest)`

---

## Reference

### System Requirements

**Minimum:**
- Python 3.10+
- Node.js 18+


**Optional:**
- Docker (for container mode)

### File Locations

**Configuration:**
- Agent config: `.agent.yaml`
- Environment: `.env` 
- Dependencies: `requirements.txt`

**Generated:**
- UI assets: `agentcli/static/` (auto-generated)
- Container server: `container_entrypoint.py`

### API Endpoints

Development server endpoints:

- `GET /` - Chat UI interface
- `POST /chat` - Agent conversation endpoint
- `GET /health` - Health check endpoint  
- `GET /info` - Agent information


### Command Reference

```bash
# Project Management
adt init <n>              # Generate new project

# Development  
adt dev                         # Start development server
adt dev --port 8083             # Custom port
adt dev --env-file .env         # Load environment file
adt dev --aws-profile prod      # Use AWS profile
adt dev --container             # Container mode
adt dev --container --rebuild   # Force a fresh container rebuild

# Tool Development
adt add tool <tool_name>          # Generate tool template
```

### Getting Help

- **Command help:** `adt --help`
- **Command-specific help:** `adt dev --help`
- **Issues:** [GitHub Issues](https://github.com/awslabs/agent-dev-toolkit/issues)
- **Strands Documentation:** [strands-agents](https://github.com/strands-agents/sdk-python)

---

**Made with ❤️ for the Strands ecosystem**