# Metadelphi - Multi-Agent LLM Studio System

A powerful, cross-platform application for comparing and interacting with multiple Large Language Models through an intuitive debate interface. Built with LangGraph, FastAPI, and a clean web interface with streaming responses.

`Metadelphi` is named for a higher-order Delphi: not a single oracle, but a council of intelligence. In the ancient Greek world, Delphi was the sacred place people turned to for guidance, judgment, and foresight. Instead of relying on one model at a time, Metadelphi brings multiple frontier models into the same reasoning loop, lets them debate, critique, and refine each other, and drives them toward a better final answer. The name signals exactly what the product is built for: orchestrated intelligence, not isolated generations.

> "Know thyself."
>
> One of the Delphic maxims, and a fitting principle for a system designed to examine problems from multiple perspectives before committing to an answer.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.txt)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#-quick-start-installation)

---

## 🚀 Quick Start Installation

### macOS / Linux (one-line installer)

```bash
curl -fsSL https://raw.githubusercontent.com/TanyuSylvain/metadelphi/main/get-metadelphi.sh | bash
```

Then open a new terminal and run:

```bash
metadelphi
```

The service will start and the web UI will open automatically. Click **Open Configuration** to add your API keys.

### Windows

Download and run `get-metadelphi.bat` from the latest release, or use PowerShell:

```powershell
powershell -Command "& { Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/TanyuSylvain/metadelphi/main/get-metadelphi.bat' -OutFile '$env:TEMP\get-metadelphi.bat'; & '$env:TEMP\get-metadelphi.bat' }"
```

Then open a new Command Prompt and run:

```bat
metadelphi
```

The service will start and the web UI will open automatically. Click **Open Configuration** to add your API keys.

### What the installer does

- ✅ Checks for Python 3.10+ and guides you to install it if missing
- ✅ Creates an isolated virtual environment
- ✅ Installs all Python dependencies
- ✅ Builds the React frontend if needed
- ✅ Installs the global `metadelphi` command
- ✅ Creates native application launchers (desktop shortcut / app icon)
- ✅ Optionally registers a per-user auto-start service at login

The application will open automatically in your browser once the service starts.

If you skip auto-start during installation, you can enable it later with:
- **Windows**: `setup_service.bat`
- **macOS/Linux**: `./setup_service.sh`

To remove auto-start later:
- **Windows**: `remove_service.bat`
- **macOS/Linux**: `./remove_service.sh`

### `metadelphi` CLI

After installation, use the `metadelphi` command from any terminal:

| Command | Description |
|---------|-------------|
| `metadelphi` | Start the background service and open the browser (default command) |
| `metadelphi start` | Start the background service and open the browser |
| `metadelphi start --no-browser` | Start the background service without opening the browser |
| `metadelphi start --port 9000` | Start on a custom port (`-p 9000` also works) |
| `metadelphi restart` | Restart the background service |
| `metadelphi restart --port 9000` | Restart on a custom port |
| `metadelphi stop` | Stop the background service |
| `metadelphi status` | Check whether the service is running |
| `metadelphi logs` | Show the latest backend log lines |
| `metadelphi logs -f` | Follow the backend log in real time |
| `metadelphi config` | Open the web UI in your browser |
| `metadelphi config --print-url` | Print the web UI URL without opening the browser |
| `metadelphi update` | Update Metadelphi to the latest release |
| `metadelphi update --version x.y.z` | Update to a specific release version |
| `metadelphi uninstall` | Remove Metadelphi from this machine (backs up data) |
| `metadelphi uninstall --remove-data` | Remove Metadelphi and delete all data |

---

## ✨ Features

### 🎯 Three Operating Modes

#### **Simple Chat Mode**
- Direct conversation with individual AI models
- Real-time streaming responses
- Fast and straightforward interaction
- Perfect for quick questions and comparisons
- Optional **web search** powered by configurable MCP servers

#### **Multi-Agent Debate Mode**
LangGraph-powered workflow with 3 specialized AI agents:
- **🎓 Moderator**: Analyzes question complexity, guides the debate process, and synthesizes the final answer
- **👨‍🔬 Expert**: Generates professional, in-depth responses with technical accuracy
- **🔍 Critic**: Reviews answers critically, identifies weaknesses, and provides constructive feedback
- **Configurable**: Adjust iteration count and quality score thresholds
- **Real-time Visualization**: Watch the debate unfold with live progress tracking

#### **Coworking Mode** *(New)*
An autonomous coding agent that works directly in your local workspace:
- **🗂️ File Operations**: Read, write, and list files within a sandboxed workspace directory
- **💻 Code Execution**: Run Python scripts and shell commands inside the workspace
- **📦 Package Management**: Automatically check and install Python packages as needed
- **🌐 Web Search**: Integrated web search via MCP servers for research during tasks
- **📁 Interactive Workspace Selection**: Native OS folder picker to choose your working directory
- **📊 Workflow Visualization**: Real-time display of tool calls, plan steps, and generated/deleted files
- **🔗 Parallel Tool Execution**: Multiple tools run concurrently for faster task completion
- **📋 File Tracking**: Session-level tracking of all files created or removed by the agent

### 🤖 Supported LLM Providers

Metadelphi supports **7 major AI providers** with multiple models:

| Provider | Models | Description |
|----------|--------|-----------|
| **Mistral AI** | `mistral-large-latest`, `mistral-medium-latest`, `mistral-small-latest`, `magistral-medium-latest`, `magistral-small-latest` | French AI, multilingual |
| **Alibaba Qwen** | `qwen3-max`, `qwen3.6-plus`, `qwen3-235b-a22b`, `qwen3.5-flash`, `qwen3-coder-plus`, `deepseek-v3.2`, `glm-5`, `kimi-k2.5` | Qwen family and partner models |
| **Zhipu GLM** | `glm-5`, `glm-4.7` | Zhipu latest general models |
| **MiniMax** | `MiniMax-M2.7-highspeed` | Top-tier deep-search model |
| **DeepSeek** | `deepseek-v4-flash`, `deepseek-v4-pro` | DeepSeek reasoning models |
| **OpenAI-compatible** | `gpt-5.5`, `gpt-5.4-mini`, `gpt-image-2` | OpenAI and compatible endpoints |
| **Google Gemini** | `gemini-3.1-pro-preview`, `gemini-3-flash-preview`, `gemini-3.1-flash-image-preview`, `gemini-2.5-flash-image` | Gemini reasoning and image models |

### 🎨 Core Features

- **🔄 Real-time Streaming**: See responses as they're generated
- **💭 Thinking Control**: Enable or disable chain-of-thought reasoning; collapsible `<think>` sections keep the UI clean
- **⛔ Cancel**: Stop any in-progress streaming request at any time
- **🌐 Web Search**: Configurable web search (Bailian / Tavily) with source citations, available in Simple and Coworking modes
- **🔌 MCP Server Support**: Configure external MCP servers for tools like web search and web parsing
- **💾 Conversation History**: Persistent storage with SQLite
- **🎨 Markdown Rendering**: Beautiful formatting for code, tables, and text
- **✨ Syntax Highlighting**: Language-aware code block highlighting in chat
- **📋 Clean Copy**: One-click copy of purified content (removes redundant spaces, blank lines, and normalizes Chinese-English formatting)
- **📱 Responsive UI**: Works on desktop, tablet, and mobile
- **🔌 REST API**: Full programmatic access with OpenAPI docs
- **🔐 Secure**: API keys stored locally in `config.toml`, locally stored chat history
- **⚡ Fast**: Optimized streaming and async processing

---

## 📋 System Requirements

- **Python 3.10 or higher** (installer will check and guide you)
- **Internet connection** (for installing dependencies and API calls)

### Supported Operating Systems
- Windows 10/11
- macOS 12+ (Monterey or later)
- Ubuntu 20.04/22.04/24.04
- Other Linux distributions with Python 3.10+

---

## 🛠️ Manual Installation (Advanced)

If you prefer manual setup or need custom configuration:

### 1. Clone or Download

```bash
git clone https://github.com/TanyuSylvain/metadelphi.git
cd metadelphi
```

### 2. Create Virtual Environment

```bash
# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate.bat
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Build the Frontend

```bash
cd frontend-react
npm install
npm run build
cd ..
```

The built files are placed in `frontend/dist-react/` and served by the backend.

### 5. Configuration (Optional)

Configuration lives in `config.toml` at the project root. Create it from the template:

```bash
# Linux/macOS
cp config.toml.template config.toml

# Windows
copy config.toml.template config.toml
```

Then edit `config.toml` with your preferred text editor. At minimum, fill in the API keys for the providers you want to use.

You can also add or edit the `[[providers.*.models]]` tables to control which models are available.

All the configurations can also be completed in the GUI. 

### 6. Launch the Application

From the project directory, start the local launcher:

```bash
# Linux/macOS
./launcher.sh

# Windows
launcher.bat
```

The application will open automatically in your browser.

If you want the global `metadelphi` command available from any terminal, run the installer instead:

```bash
# Linux/macOS
./install.sh

# Windows
install.bat
```

Then you can use `metadelphi start` from a new terminal.

---

## 🎮 Using Metadelphi

### Starting a Simple Chat

1. Select a **provider and model** from the dropdown
2. Choose **"Simple Mode"**
3. Type your message and press Enter or click Send
4. Watch the streaming response appear in real-time

### Running a Multi-Agent Debate

1. Choose **"Debate Mode"**
2. Configure debate settings:
   - **Maximum Iterations**: How many rounds of debate (1-10)
   - **Score Threshold**: Minimum quality score to accept (0-100)
3. Select the model for each agent role
4. Ask your question
5. Watch the agents debate and arrive at a consensus!

### Using Coworking Mode

1. Choose **"Coworking"** mode
2. Click **Browse** to select a local workspace directory
3. Ask the agent to complete a coding task (write a script, refactor code, run tests, etc.)
4. Watch the agent's plan, tool calls, and file changes in the workflow panel
5. Click **Cancel** at any time to stop the agent mid-task

The agent has access to:
- Read/write files within the workspace
- Execute Python scripts and shell commands
- Install Python packages
- Search the web (if MCP servers are configured)

### Enabling Web Search

Web search is configured in `config.toml` under the `[web_search]` section. The simplest option is to add a Bailian (DashScope) API key:

```toml
[web_search]
default_engine = "bailian"
bailian_api_key = "your_bailian_api_key"
tavily_api_key = "your_tavily_api_key"  # optional alternative
```

Once a search backend is configured, a **Search** toggle appears in Simple and Coworking modes.

For additional tool capabilities, you can also configure MCP servers under the `[mcp]` table:

```toml
[[mcp.servers]]
name = "websearch"
url = "https://your-mcp-server-url/sse"
transport = "sse"
```


### Managing Conversations

- **New Conversation**: Click the "+" button in the sidebar
- **Switch Conversations**: Click any conversation in the history
- **Delete Conversations**: Click the trash icon
- **Export**: Conversations are automatically saved to SQLite

---

## 🔌 API Documentation

Full interactive API documentation is available at:
**http://localhost:8000/docs** (when backend is running on the default port)

### Key Endpoints

#### Chat Endpoints
- `POST /chat/` - Simple chat (complete response)
- `POST /chat/stream` - Simple streaming chat
  ```json
  {
    "message": "Your question here",
    "model": "mistral-large-latest",
    "conversation_id": "optional-uuid"
  }
  ```
- `POST /chat/image/stream` - Image generation streaming
- `POST /chat/multi-agent/` - Multi-agent debate (complete response)
- `POST /chat/multi-agent/stream` - Multi-agent debate streaming
  ```json
  {
    "message": "Your question here",
    "models": {
      "moderator": "mistral-large-latest",
      "expert": "qwen-max",
      "critic": "glm-4-plus"
    },
    "max_iterations": 3,
    "score_threshold": 80
  }
  ```
- `POST /chat/coworking/stream` - Coworking agent with tool calling
  ```json
  {
    "message": "Write a Python script that...",
    "model": "qwen-max",
    "workspace_path": "/path/to/your/workspace",
    "conversation_id": "optional-uuid"
  }
  ```
- `GET /chat/coworking/select-workspace` - Open native folder picker
- `GET /chat/coworking/session-state` - Get coworking file-tracking state
- `GET /chat/coworking/files` - Download a file from the workspace
- `POST /chat/coworking/open-file` - Open a workspace file with the default app
- `POST /chat/runs/{run_id}/cancel` - Cancel an active streaming run

#### Model Management
- `GET /models` - List all available models
- `GET /models/providers` - List all providers
- `GET /models/providers/{provider_name}` - Get provider info and models
- `GET /models/{model_id}/provider` - Find provider for a model ID

#### Conversation Management
- `GET /conversations/` - List all conversations
- `POST /conversations/` - Create new conversation
- `GET /conversations/{conversation_id}` - Get conversation history
- `GET /conversations/{conversation_id}/info` - Get conversation metadata
- `DELETE /conversations/{conversation_id}` - Delete conversation
- `DELETE /conversations/` - Delete all conversations
- `POST /conversations/{conversation_id}/switch-mode` - Switch conversation mode

#### Settings & Configuration
- `GET /settings/config` - Get full application config
- `PUT /settings/config` - Update and persist full config
- `GET /settings/providers` - Get provider settings with masked keys
- `POST /settings/providers/test-model` - Test a provider/model
- `POST /settings/providers/{provider_id}/models/{model_id}/test` - Test saved provider/model
- `GET /settings/search-engine` - Get search engine status
- `PUT /settings/search-engine` - Update default search engine

#### Health & Monitoring
- `GET /health` - Backend health check
- `GET /info` - API information

---


## 🔄 Updating Metadelphi

The easiest way to update is with the CLI:

```bash
metadelphi update
```

This stops the service, downloads the latest release, preserves your `config.toml` and conversations, and restarts the service.

To install a specific version:

```bash
metadelphi update --version x.y.z
```

### Manual update

Alternatively, you can update manually:

1. Backup your `config.toml` file (contains your API keys)
2. Download the new version
3. Extract to a new directory
4. Copy your `config.toml` file to the new directory
5. Run the installer again (it will update dependencies)

If using git:

```bash
# Backup your config.toml file
cp config.toml config.toml.backup

# Pull latest changes
git pull origin main

# Reinstall dependencies
pip install -r requirements.txt

# Restore your config.toml
cp config.toml.backup config.toml
```

---

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- **Provider Integrations**: Add support for new LLM providers
- **UI Enhancements**: Improve design, add themes, accessibility
- **Features**: New debate modes, export options, analytics
- **Performance**: Optimize streaming, caching, async operations
- **Documentation**: Tutorials, examples, API guides
- **Testing**: Unit tests, integration tests, E2E tests
- **Bug Fixes**: Report and fix issues

### Development Setup

```bash
# Clone the repository
git clone https://github.com/TanyuSylvain/metadelphi.git
cd metadelphi

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate.bat on Windows

# Install dependencies
pip install -r requirements.txt

# Configure application
cp config.toml.template config.toml
# Add your API keys to the [providers.*] sections

# Build the React frontend
cd frontend-react
npm install
npm run build

# Run backend in development mode from the repo root
cd ..
python -m backend.main
```

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE.txt](LICENSE.txt) for details.

---
