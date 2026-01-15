# 🔍 Local Code Review & Fix Agent

A privacy-first Python web application that reviews, explains, and iteratively fixes Python code using a self-healing agent loop. **Fully offline** — no cloud APIs required.

## ✨ Features

- **🔒 Privacy First**: All processing happens locally using Ollama. Your code never leaves your machine.
- **🔄 Self-Healing Loop**: Automatically retries fixing code until it executes successfully.
- **📋 Detailed Reviews**: Get comprehensive code reviews with issues, suggestions, and severity ratings.
- **🚀 Sandboxed Execution**: Safely execute code with timeout protection and blocked imports.
- **💬 Chat Interface**: Intuitive Streamlit-based chat UI for interaction.

## 🏗️ Architecture

```
code-review-agent/
├── app.py                    # Streamlit entry point
├── config.py                 # Settings (model name, max retries, timeout)
├── agents/
│   ├── graph.py              # LangGraph state machine
│   └── prompts.py            # System prompts for review/fix tasks
├── tools/
│   ├── executor.py           # Safe code execution (subprocess, tempfile)
│   └── linter.py             # AST-based safety checks
├── models/
│   └── schemas.py            # Pydantic models for structured outputs
├── ui/
│   └── components.py         # Reusable Streamlit components
└── utils/
    └── helpers.py            # Shared utilities
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+** installed
2. **Ollama** installed and running ([Install Ollama](https://ollama.ai/))
3. A code model pulled in Ollama:

```bash
# Recommended model (requires ~2GB RAM)
ollama pull qwen3:1.7b

# Alternative options (require more RAM)
ollama pull qwen3:8b           # ~8GB RAM needed
ollama pull codellama:7b       # ~8GB RAM needed
```

### Installation

```bash
# Clone the repository (or navigate to the project)
cd code-review-agent

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the App

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

## 📖 Usage

1. **Enter Code**: Paste your Python code in the text area or upload a `.py` file.
2. **Review & Fix**: Click the "🔍 Review & Fix" button to start the agent.
3. **View Results**: See the review, fixes, and execution results in separate tabs.
4. **Iterate**: Make follow-up requests in the chat to refine the code.

## ⚙️ Configuration

Adjust settings in the sidebar:

| Setting | Default | Description |
|---------|---------|-------------|
| Ollama Model | `qwen3:1.7b` | The LLM model to use |
| Max Retries | `3` | Max attempts to fix failing code |
| Timeout | `10s` | Execution timeout |
| Temperature | `0.1` | LLM creativity (lower = more deterministic) |

## 🔒 Security

The executor blocks potentially dangerous imports:

- `os`, `sys`, `subprocess`, `shutil`
- `socket`, `requests`, `urllib`, `http`
- `pickle`, `marshal`, `ctypes`
- `builtins`, `importlib`

Code is executed in an isolated subprocess with strict timeout enforcement.

## 🔄 Agent Flow

```
START → review → fix → execute → evaluate
                          ↑          ↓
                          └── retry ←┘ (if error & attempts < max)
                                     ↓
                                   END (success or max retries)
```

## 🛠️ Development

### Project Structure

- **`config.py`**: Centralized configuration with sensible defaults
- **`models/schemas.py`**: Pydantic models for type-safe LLM outputs
- **`tools/executor.py`**: Sandboxed code execution
- **`tools/linter.py`**: AST-based safety analysis
- **`agents/graph.py`**: LangGraph state machine with retry logic
- **`agents/prompts.py`**: Carefully crafted system prompts
- **`ui/components.py`**: Reusable Streamlit UI components
- **`app.py`**: Main Streamlit application

### Extending the Agent

To add new capabilities:

1. Add new nodes in `agents/graph.py`
2. Define new Pydantic schemas in `models/schemas.py`
3. Create UI components in `ui/components.py`
4. Update prompts in `agents/prompts.py`

## 📝 License

MIT License - Feel free to use and modify for your projects.

## 🤝 Contributing

Contributions welcome! Please feel free to submit issues and pull requests.

---

**Built with** ❤️ **using Streamlit, LangChain, LangGraph, and Ollama**
