# UnifyLLM - Multi-Agent LLM Studio System

A powerful, cross-platform application for comparing and interacting with multiple Large Language Models through an intuitive debate interface. Built with LangGraph, FastAPI, and a clean web interface with streaming responses.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.txt)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#-quick-start-installation)

---

## 🚀 Quick Start Installation

### Windows
1. Download the Windows installer package (ZIP file)
2. Right-click the ZIP file → "Extract All..." → Choose destination
3. Open the extracted folder
4. Double-click `install.bat`
5. Follow the on-screen instructions
6. Configure your API keys in the GUI wizard
7. Launch using the desktop shortcut or run `launcher.bat`

### macOS
1. Download the installer package (TAR.GZ file)
2. Extract the archive: Double-click or run `tar -xzf unify_llm.tar.gz` in Terminal
3. Open Terminal and navigate to the extracted directory: `cd unify_llm`
4. Run: `./install.sh`
5. Follow the on-screen instructions
6. Configure your API keys in the GUI wizard
7. Launch from **Launchpad** or **~/Applications/UnifyLLM.app**

### Linux
1. Download the installer package (TAR.GZ file)
2. Extract the archive: `tar -xzf unify_llm.tar.gz`
3. Navigate to the extracted directory: `cd unify_llm`
4. Run: `./install.sh`
5. Follow the on-screen instructions
6. Configure your API keys in the GUI wizard
7. Launch from your **Application Menu** or Desktop launcher

**That's it!** The installer automatically:
- ✅ Checks for Python 3.10+ (guides you to install if missing)
- ✅ Creates an isolated virtual environment
- ✅ Installs all dependencies (including SOCKS proxy support)
- ✅ Launches a GUI wizard to configure API keys
- ✅ Creates native application launchers:
  - **macOS**: UnifyLLM.app in ~/Applications (appears in Launchpad)
  - **Linux**: Desktop entry in Application Menu
  - **Windows**: Desktop shortcut
- ✅ Opens the application in your browser automatically

The application will be available at: **http://localhost:8080/index.html**

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

UnifyLLM supports **7 major AI providers** with multiple models:

| Provider | Models | Description |
|----------|--------|-----------|
| **Mistral AI** | Mistral Large, Medium, Small, and Magistral Medium, Small | French AI, multilingual |
| **Alibaba Qwen** | Qwen3 Max, Plus, 235b, DeepSeek V3.2, GLM-4.7, Kimi K2 | Qwen family cutting-edge models |
| **Zhipu GLM** | GLM 4.7, GLM 4.6 | Zhipu latest general models |
| **MiniMax** | MiniMax-M2.1 | I love it, top 1, suitable for deep search |
| **DeepSeek** | DeepSeek Chat, Reasoner (V3.2) | Use it if you like |
| **OpenAI-compatible** | GPT-5.2 | Still testing |
| **Google Gemini** | Gemini 3 pro preview, flash | Still testing |

### 🎨 Core Features

- **🔄 Real-time Streaming**: See responses as they're generated
- **💭 Thinking Control**: Enable or disable chain-of-thought reasoning; collapsible `<think>` sections keep the UI clean
- **⛔ Cancel**: Stop any in-progress streaming request at any time
- **🌐 Web Search**: MCP-powered web search with source citations, available in Simple and Coworking modes
- **🔌 MCP Server Support**: Configure external MCP servers for tools like web search and web parsing
- **💾 Conversation History**: Persistent storage with SQLite
- **🎨 Markdown Rendering**: Beautiful formatting for code, tables, and text
- **✨ Syntax Highlighting**: Language-aware code block highlighting in chat
- **📋 Clean Copy**: One-click copy of purified content (removes redundant spaces, blank lines, and normalizes Chinese-English formatting)
- **📱 Responsive UI**: Works on desktop, tablet, and mobile
- **🔌 REST API**: Full programmatic access with OpenAPI docs
- **🔐 Secure**: API keys stored locally in `.env` file, locally stored chat history
- **⚡ Fast**: Optimized streaming and async processing

---

## 📋 System Requirements

- **Python 3.10 or higher** (installer will check and guide you)
- **Internet connection** (for installing dependencies and API calls)
- **At least one LLM provider API key** (see below)

### Supported Operating Systems
- Windows 10/11
- macOS 12+ (Monterey or later)
- Ubuntu 20.04/22.04/24.04
- Other Linux distributions with Python 3.10+

---

## 🔑 Getting API Keys

Each provider requires an API key. Most offer **free tiers** or trial credits:

1. **Mistral AI**
   - Get key: https://console.mistral.ai/
   - Free tier available

2. **Alibaba Qwen (DashScope)**
   - Get key: https://dashscope.aliyuncs.com/
   - Registration required

3. **Zhipu GLM**
   - Get key: https://open.bigmodel.cn/
   - Chinese registration

4. **MiniMax**
   - Get key: https://www.minimaxi.com/
   - Free credits available

5. **DeepSeek**
   - Get key: https://platform.deepseek.com/
   - Competitive pricing

6. **OpenAI**
   - Get key: https://platform.openai.com/api-keys
   - Pay-as-you-go pricing

7. **Google Gemini**
   - Get key: https://makersuite.google.com/app/apikey
   - Free tier available

> 💡 **Tip**: You only need ONE API key to start, but more providers give you better comparisons!

---

## 🛠️ Manual Installation (Advanced)

If you prefer manual setup or need custom configuration:

### 1. Clone or Download

```bash
git clone https://github.com/your-repo/unify_llm.git
cd unify_llm
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

### 4. Configure API Keys

**Option A: Use the GUI Configuration Wizard (Recommended)**

```bash
python installer/config_wizard.py
```

The wizard provides:
- Easy-to-use graphical interface
- Direct links to get API keys
- Password-style entry with show/hide toggle
- Validation and status tracking

**Option B: Manual Configuration**

Copy `.env.template` to `.env` and add your API keys:

```bash
# Linux/macOS
cp .env.template .env

# Windows
copy .env.template .env
```

Then edit `.env` with your preferred text editor:

```bash
# Mistral AI
MISTRAL_API_KEY=your_key_here

# Alibaba Qwen (DashScope)
QWEN_API_KEY=your_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# Zhipu GLM
GLM_API_KEY=your_key_here
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4

# MiniMax
MINIMAX_API_KEY=your_key_here
MINIMAX_BASE_URL=https://api.minimax.io/v1

# DeepSeek
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# OpenAI or OpenAI-compatible
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# Google Gemini
GEMINI_API_KEY=your_key_here
GEMINI_BASE_URL=https://generativelanguage.googleapis.com

# MCP Servers for web search and web parsing (optional, JSON array)
# MCP_SERVERS='[{"name":"websearch","url":"<server-url>","transport":"sse","api_key":"<optional-key>"}]'
```

### 5. Launch the Application

```bash
# Linux/macOS
./launcher.sh

# Windows
launcher.bat
```

The application will open automatically in your browser at:
**http://localhost:8080/index.html**

---

## 🎮 Using UnifyLLM

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

Web search is powered by MCP servers. To enable it, set `MCP_SERVERS` in your `.env` file:

```bash
# JSON array of MCP server configurations
MCP_SERVERS='[{"name":"websearch","url":"<your-mcp-server-url>","transport":"sse"}]'
```

Once configured, a **Search** toggle appears in Simple and Coworking modes.


### Managing Conversations

- **New Conversation**: Click the "+" button in the sidebar
- **Switch Conversations**: Click any conversation in the history
- **Delete Conversations**: Click the trash icon
- **Export**: Conversations are automatically saved to SQLite

---

## 🏗️ Architecture

### Backend (Python/FastAPI)

```
backend/
├── main.py                          # FastAPI application entry point
├── config.py                        # Configuration and environment variables
├── api/
│   ├── routes/
│   │   ├── chat.py                  # Simple streaming chat endpoint
│   │   ├── multi_agent_chat.py      # Multi-agent debate endpoint
│   │   ├── coworking_chat.py        # Coworking agent endpoint (NEW)
│   │   ├── run_control.py           # Cancel active streaming runs (NEW)
│   │   ├── conversations.py         # Conversation CRUD operations
│   │   ├── models.py                # List available models
│   │   └── health.py                # Health check endpoint
│   ├── run_control.py               # RunManager for cancellation state (NEW)
│   └── schemas.py                   # Pydantic data models
├── core/
│   ├── multi_agent.py               # LangGraph workflow orchestration
│   ├── multi_agent_state.py         # State management for debates
│   ├── coworking_agent.py           # LangGraph tool-calling coworking agent (NEW)
│   ├── coworking_state.py           # Coworking session state (NEW)
│   ├── coworking_prompts.py         # System prompts for coworking agent (NEW)
│   ├── run_manager.py               # Cancellable run lifecycle management (NEW)
│   ├── conversation_mode_manager.py # Mode switching logic
│   └── prompts.py                   # System prompts for debate agents
├── tools/
│   ├── workspace_tools.py           # Sandboxed file/shell tools for coworking (NEW)
│   └── web_search.py                # MCP-backed web search tools (NEW)
├── providers/
│   ├── factory.py                   # LLM provider factory
│   ├── base.py                      # Base provider interface
│   ├── registry.py                  # Provider registration
│   ├── mistral.py                   # Mistral AI integration
│   ├── qwen.py                      # Qwen/DashScope integration
│   ├── glm.py                       # Zhipu GLM integration
│   ├── minimax.py                   # MiniMax integration
│   ├── deepseek.py                  # DeepSeek integration
│   ├── openai_compatible.py         # OpenAI-compatible APIs
│   └── gemini.py                    # Google Gemini integration
├── storage/
│   ├── base.py                      # Storage interface
│   ├── sqlite.py                    # SQLite implementation
│   └── memory.py                    # In-memory storage (testing)
└── utils/                           # Utility functions
```

### Frontend (Vanilla JS)

```
frontend/src/
├── index.html                       # Main HTML page
├── app.js                           # Application entry point
├── components/
│   ├── ModelSelector.js             # Model selection dropdown
│   ├── Sidebar.js                   # Conversation history sidebar
│   ├── MessageComponent.js          # Chat message rendering (syntax highlighting)
│   ├── ModeSelector.js              # Simple/Debate/Coworking mode toggle
│   ├── MultiAgentConfig.js          # Debate configuration panel
│   ├── DebateViewer.js              # Real-time debate visualization
│   ├── ModeratorAnalysisViewer.js   # Moderator insights display
│   ├── CoworkingConfig.js           # Workspace path selector (NEW)
│   └── ToolExecutionViewer.js       # Coworking tool calls & file tracker (NEW)
├── utils/
│   ├── api.js                       # API client wrapper
│   ├── helpers.js                   # Helper functions
│   ├── markdown.js                  # Markdown rendering
│   └── smartScroller.js             # Smart auto-scroll utility (NEW)
└── styles/                          # CSS stylesheets
```

### Installation System

```
installer/
├── config_wizard.py                 # GUI configuration wizard (Tkinter)
├── create_launcher.py               # Desktop launcher creator (Unix)
├── create_shortcut.py               # Desktop shortcut creator (Windows)
├── generate_icons.py                # Icon generator
├── icon.png                         # Application icon (PNG)
└── icon.ico                         # Application icon (Windows ICO)
```

---

## 🔌 API Documentation

Full interactive API documentation is available at:
**http://localhost:8000/docs** (when backend is running)

### Key Endpoints

#### Chat Endpoints
- `POST /chat/stream` - Simple streaming chat
  ```json
  {
    "message": "Your question here",
    "provider_name": "mistral",
    "model_name": "mistral-large-latest",
    "conversation_id": "optional-uuid"
  }
  ```

- `POST /chat/multi-agent` - Multi-agent debate mode
  ```json
  {
    "message": "Your question here",
    "moderator_model": "mistral-large-latest",
    "expert_model": "qwen-max",
    "critic_model": "glm-4",
    "max_iterations": 3,
    "score_threshold": 80
  }
  ```

- `POST /chat/coworking/stream` - Coworking agent with tool calling
  ```json
  {
    "message": "Write a Python script that...",
    "model_id": "qwen-max",
    "workspace_path": "/path/to/your/workspace",
    "conversation_id": "optional-uuid"
  }
  ```

- `POST /chat/runs/{run_id}/cancel` - Cancel an active streaming run

#### Model Management
- `GET /models/` - List all available models
- `GET /models/{provider_name}` - List models for specific provider

#### Conversation Management
- `GET /conversations` - List all conversations
- `POST /conversations` - Create new conversation
- `GET /conversations/{id}` - Get conversation details
- `DELETE /conversations/{id}` - Delete conversation

#### Health & Monitoring
- `GET /health` - Backend health check
- `GET /` - API information

---

## 🐛 Troubleshooting

### Installation Issues

**Problem: Python not found**
- **Windows**: Install from https://python.org (check "Add Python to PATH")
- **macOS**: `brew install python@3.11`
- **Linux**: `sudo apt install python3.11 python3.11-venv python3-pip`

**Problem: Tkinter not available (Linux)**
```bash
sudo apt install python3-tk
```

**Problem: Permission denied (Unix)**
```bash
chmod +x install.sh launcher.sh
```

**Problem: Virtual environment creation fails**
- Ensure `python3-venv` is installed (Linux)
- Check disk space availability
- Try running with administrator/sudo privileges

### Runtime Issues

**Problem: Port already in use**
- Check if ports 8000 or 8080 are occupied
- Stop conflicting services
- Change ports in `backend/config.py` if needed

**Problem: API key errors**
- Verify keys are correct in `.env`
- Ensure no extra spaces or quotes in `.env` file
- Check API key has sufficient credits/quota
- Test API key with provider's official tools

**Problem: Browser doesn't open automatically**
- Manually navigate to http://localhost:8080/index.html
- Check firewall settings
- Verify both backend and frontend servers started

**Problem: Streaming responses not working**
- Check browser console for errors (F12)
- Verify backend is running on port 8000
- Check CORS settings if accessing from different domain

**Problem: Models not appearing**
- Ensure at least one API key is configured
- Check backend logs for provider initialization errors
- Verify API keys are valid and active

### Getting Help

1. Check the console output for error messages
2. Verify your `.env` configuration
3. Test with a single provider first
4. Check provider status pages for API outages
5. Create an issue on GitHub with:
   - Your operating system and Python version
   - Error messages from console/logs
   - Steps to reproduce the problem

---

## 🔄 Updating UnifyLLM

To update to a new version:

1. Backup your `.env` file (contains your API keys)
2. Download the new version
3. Extract to a new directory
4. Copy your `.env` file to the new directory
5. Run the installer again (it will update dependencies)

Alternatively, if using git:

```bash
# Backup your .env file
cp .env .env.backup

# Pull latest changes
git pull origin main

# Reinstall dependencies
pip install -r requirements.txt

# Restore your .env
cp .env.backup .env
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
git clone https://github.com/your-repo/unify_llm.git
cd unify_llm

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate.bat on Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Add your API keys

# Run backend in development mode
cd backend
python -m uvicorn main:app --reload --port 8000

# In another terminal, serve frontend
cd frontend/src
python -m http.server 8080
```

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE.txt](LICENSE.txt) for details.

---

