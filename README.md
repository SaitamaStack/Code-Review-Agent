# 🔍 Local Code Review & Fix Agent

A privacy-first Python desktop application that reviews, explains, and iteratively fixes Python code using a self-healing agent loop. **Fully offline** — no cloud APIs required.

## ✨ Features

- **🔒 Privacy First**: All processing happens locally using Ollama. Your code never leaves your machine.
- **🔄 Self-Healing Loop**: Automatically retries fixing code until it executes successfully.
- **📋 Detailed Reviews**: Get comprehensive code reviews with issues, suggestions, and severity ratings.
- **🚀 Sandboxed Execution**: Safely execute code with timeout protection and blocked imports.
- **🖥️ Modern Desktop UI**: Beautiful dark-themed CustomTkinter interface.

## 🛠️ Tech Stack

- **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** - Modern desktop UI framework
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** - Agent state machine for review-fix-execute workflow
- **[Ollama](https://ollama.ai/)** - Local LLM inference
- **[Pydantic](https://docs.pydantic.dev/)** - Structured LLM output validation

## 🏗️ Project Structure

```
code-review-agent/
├── app.py                    # CustomTkinter desktop application
├── config.py                 # Settings (model name, max retries, timeout)
├── requirements.txt          # Python dependencies
├── test_parsing.py           # LLM response parsing test utility
├── agents/
│   ├── __init__.py           # Package exports
│   ├── graph.py              # LangGraph state machine
│   └── prompts.py            # System prompts for review/fix tasks
├── tools/
│   ├── __init__.py           # Package exports
│   ├── executor.py           # Safe code execution (subprocess, tempfile)
│   └── linter.py             # AST-based safety checks
├── models/
│   ├── __init__.py           # Package exports
│   └── schemas.py            # Pydantic models for structured outputs
└── utils/
    ├── __init__.py           # Package exports
    └── helpers.py            # Shared utilities
```

## 🚀 Quick Start

## System Requirements

**Hardware:**
- **GPU**: NVIDIA GPU with 12GB+ VRAM (required)
- **Tested on**: RTX 5070 (12GB), RTX 3060 (12GB), RTX 4060 Ti (16GB), RTX 3090 Ti (24GB)
- **RAM**: 16GB+ system RAM recommended
- **Storage**: ~15GB free space for model download

**Software:**
- Python 3.8+
- Ollama installed and running
- CUDA-compatible drivers (for NVIDIA GPUs)

**Model:**
- qwen3:14b (automatically downloaded on first run via Ollama)

**Why qwen3:14b?**

After benchmark analysis, qwen3:14b was selected as the minimum viable model for reliable code review:

- Matches the performance of Qwen2.5-32B (2x its size) on coding benchmarks
- Outperforms Qwen2.5-14B on STEM and coding tasks despite being a newer, more efficient architecture  
- Testing revealed that models below 14b parameters struggled to consistently detect security vulnerabilities (like unsafe eval() usage) and complex runtime errors

This model requires significant GPU resources and targets desktop workstations. It is not suitable for CPU-only systems or laptops without dedicated graphics cards.

### Prerequisites

1. **Python 3.8+** installed
2. **Ollama** installed and running ([Install Ollama](https://ollama.ai/))
3. Pull the required model:

```bash
ollama pull qwen3:14b
```

### Installation

```bash
# Clone the repository (or navigate to the project)
cd code-review-agent

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the App

```bash
python app.py
```

The desktop application will launch with a dark-themed interface.

## 📖 Usage

1. **Enter Code**: Paste your Python code in the text area or click "Upload File" to load a `.py` file.
2. **Review & Fix**: Click the "🔍 Review & Fix" button to start the agent.
3. **View Results**: See the review, fixes, execution results, and diff in separate tabs.
4. **Execute Only**: Use "🚀 Execute Only" to run code without review.

## ⚙️ Configuration

Adjust settings in the sidebar:

| Setting | Default | Description |
|---------|---------|-------------|
| Ollama Model | `qwen3:14b` | The LLM model to use |
| Ollama Base URL | `http://localhost:11434` | Ollama server address |
| Max Retries | `3` | Max attempts to fix failing code |
| Timeout | `10s` | Execution timeout per attempt |
| Temperature | `0.1` | LLM creativity (lower = more deterministic) |

## 🔒 Security

The executor blocks potentially dangerous imports:

- `os`, `sys`, `subprocess`, `shutil`
- `socket`, `requests`, `urllib`, `http`
- `pickle`, `marshal`, `ctypes`
- `builtins`, `importlib`

Code is executed in an isolated subprocess with strict timeout enforcement.

## 🔄 Agent Workflow

```
START → review → fix → execute → evaluate
                          ↑          ↓
                          └── retry ←┘ (if error & attempts < max)
                                     ↓
                                   END (success or max retries)
```

The agent uses LangGraph to orchestrate a self-healing loop:
1. **Review**: LLM analyzes code for bugs and security issues
2. **Fix**: LLM generates corrected code based on review
3. **Execute**: Code runs in sandboxed subprocess
4. **Evaluate**: Check results, retry if needed

## 📝 License

MIT License - Feel free to use and modify for your projects.

---

**Built with** ❤️ **using CustomTkinter, LangChain, LangGraph, and Ollama**
