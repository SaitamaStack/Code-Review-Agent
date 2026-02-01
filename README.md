# 🔍 Local Code Review & Fix Agent

A privacy-first Python desktop application that reviews, explains, and iteratively fixes Python code using a self-healing agent loop. **Fully offline** — no cloud APIs required.

## ✨ Features

- **🔒 Privacy First**: All processing happens locally using Ollama. Your code never leaves your machine.
- **🔄 Self-Healing Loop**: Automatically retries fixing code until it executes successfully.
- **📋 Detailed Reviews**: Get comprehensive code reviews with issues, suggestions, and severity ratings.
- **🚀 Sandboxed Execution**: Safely execute code with timeout protection and blocked imports.
- **🖥️ Modern Desktop UI**: Beautiful dark-themed CustomTkinter interface.

---

## 📋 Prerequisites

### 1. Ollama (Required)

This application uses **Ollama** to run AI models locally. Ollama must be installed and running before launching the app.

**Install Ollama:**
- **Download**: [https://ollama.com](https://ollama.com)
- **Windows**: Run the installer
- **macOS**: `brew install ollama` or download from website
- **Linux**: `curl -fsSL https://ollama.com/install.sh | sh`

**Verify Installation:**
```bash
ollama --version
```

### 2. Pull the Required Model

After installing Ollama, download the AI model:

```bash
ollama pull qwen3:14b
```

> ⏱️ **Note**: This downloads ~9GB. It only needs to be done once.

### 3. Ensure Ollama is Running

Ollama typically starts automatically after installation. Verify it's running:

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it:
ollama serve
```

> 💡 **Tip**: On Windows/macOS, Ollama runs as a system service. On Linux, you may need to run `ollama serve` in a terminal.

---

## 🚀 Installation

### Option 1: Download Pre-Built Executable (Recommended)

1. Download the latest release from the [Releases](../../releases) page
2. Extract the archive
3. Run `CodeReviewAgent.exe` (Windows) or `CodeReviewAgent` (Linux/macOS)

> ⚠️ **Important**: Make sure Ollama is running before launching the app!

### Option 2: Run from Source

```bash
# Clone the repository
git clone <repository-url>
cd code-review-agent

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### Option 3: Build from Source

See [Building from Source](#-building-from-source) section below.

---

## 💻 System Requirements

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **GPU** | NVIDIA 8GB+ VRAM | NVIDIA 12GB+ VRAM |
| **RAM** | 16GB | 32GB |
| **Storage** | 15GB free | 20GB free |

**Tested GPUs**: RTX 3060 (12GB), RTX 4060 Ti (16GB), RTX 5070 (12GB), RTX 3090 Ti (24GB)

### Software

- **OS**: Windows 10/11, macOS 11+, Ubuntu 20.04+
- **Python**: 3.8+ (for running from source)
- **Ollama**: Latest version
- **CUDA**: 11.8+ (for NVIDIA GPU acceleration)

### Why qwen3:14b?

After benchmark analysis, **qwen3:14b** was selected as the minimum viable model:

- Matches performance of Qwen2.5-32B on coding benchmarks
- Reliably detects security vulnerabilities and runtime errors
- 14B parameters is the sweet spot for accuracy vs. speed
- Uses 8K context window for thorough code analysis

> ⚠️ **Note**: This model requires a dedicated GPU. CPU-only systems will be extremely slow. The 8K context window provides better bug detection but uses more VRAM (~8-10GB) and processes slower than smaller contexts.

---

## 📖 Usage

1. **Launch the App**: Double-click the executable or run `python app.py`
2. **Enter Code**: Paste Python code or click "📂 Upload File"
3. **Review & Fix**: Click "🔍 Review & Fix" to start the agent
4. **View Results**: Check the tabs for Review, Fixed Code, Execution, and Diff

### Quick Actions

| Button | Description |
|--------|-------------|
| **🔍 Review & Fix** | Full analysis: review → fix → execute → retry |
| **🚀 Execute Only** | Run code without LLM review |
| **📂 Upload File** | Load a `.py` file from disk |

---

## ⚙️ Configuration

Adjust settings in the sidebar:

| Setting | Default | Description |
|---------|---------|-------------|
| **Ollama Model** | `qwen3:14b` | LLM model to use |
| **Ollama Base URL** | `http://localhost:11434` | Ollama server address |
| **Max Retries** | `3` | Max attempts to fix code |
| **Timeout** | `10s` | Execution timeout per attempt |
| **Temperature** | `0.1` | LLM creativity (lower = deterministic) |

---

## 🔨 Building from Source

### Prerequisites

- Python 3.8+
- pip
- PyInstaller (`pip install pyinstaller`)

### Build Steps

**Windows:**
```batch
# Run the build script
build.bat
```

**Linux/macOS:**
```bash
# Make script executable
chmod +x build.sh

# Run the build script
./build.sh
```

### Manual Build

```bash
# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Build with spec file
pyinstaller code_review_agent.spec --clean --noconfirm
```

The executable will be in `dist/CodeReviewAgent` (or `dist/CodeReviewAgent.exe` on Windows).

### Adding a Custom Icon

1. Create or obtain an icon:
   - Windows: `app.ico` (256x256, multi-resolution)
   - macOS: `app.icns`
   - Linux: `app.png` (256x256 or 512x512)

2. Place in `assets/` folder

3. Edit `code_review_agent.spec`, uncomment the icon line:
   ```python
   icon='assets/app.ico',  # Windows
   # icon='assets/app.icns',  # macOS
   ```

4. Rebuild

---

## 🔧 Troubleshooting

### "Ollama Not Running" Error

**Problem**: App shows error dialog about Ollama not being detected.

**Solutions**:
1. **Install Ollama**: Download from [ollama.com](https://ollama.com)
2. **Start Ollama**: 
   - Windows/macOS: Should auto-start; check system tray
   - Linux: Run `ollama serve` in a terminal
3. **Check connection**: `curl http://localhost:11434/api/tags`

### "Model Not Found" Error

**Problem**: LLM requests fail with model errors.

**Solution**: Pull the required model:
```bash
ollama pull qwen3:14b
```

List available models:
```bash
ollama list
```

### Slow Performance

**Problem**: Code review takes a very long time.

**Solutions**:
1. **Use GPU**: Ensure NVIDIA drivers and CUDA are installed
2. **Check GPU usage**: Run `nvidia-smi` while the app is processing
3. **Try smaller model**: In settings, change model to `qwen3:8b` (faster but less accurate)

### "Connection Refused" Error

**Problem**: Can't connect to Ollama.

**Solutions**:
1. Check Ollama is running: `ollama serve`
2. Check URL in settings matches Ollama's address
3. Firewall may be blocking port 11434
4. WSL users: Use `http://host.docker.internal:11434` or your host IP

### Build Fails (PyInstaller)

**Problem**: PyInstaller build fails with missing modules.

**Solutions**:
1. Install all dependencies: `pip install -r requirements.txt`
2. Windows antivirus may quarantine files—add exception
3. Try upgrading PyInstaller: `pip install --upgrade pyinstaller`
4. Check for tkinter: 
   - Ubuntu: `sudo apt install python3-tk`
   - Fedora: `sudo dnf install python3-tkinter`

### App Crashes on Startup

**Problem**: Executable crashes immediately.

**Solutions**:
1. Run from terminal to see error: `./dist/CodeReviewAgent` or `dist\CodeReviewAgent.exe`
2. Ensure all dependencies were bundled (rebuild with `--clean`)
3. Check antivirus isn't blocking the executable

---

## 🛠️ Tech Stack

- **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** - Modern desktop UI framework
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** - Agent state machine for review-fix-execute workflow
- **[Ollama](https://ollama.ai/)** - Local LLM inference
- **[Pydantic](https://docs.pydantic.dev/)** - Structured LLM output validation
- **[PyInstaller](https://pyinstaller.org/)** - Executable packaging

---

## 🏗️ Project Structure

```
code-review-agent/
├── app.py                    # Main desktop application
├── config.py                 # Application settings
├── requirements.txt          # Python dependencies
├── code_review_agent.spec    # PyInstaller build configuration
├── build.bat                 # Windows build script
├── build.sh                  # Linux/macOS build script
├── agents/
│   ├── __init__.py           # Package exports
│   ├── graph.py              # LangGraph state machine
│   └── prompts.py            # System prompts for review/fix
├── tools/
│   ├── __init__.py           # Package exports
│   ├── executor.py           # Safe code execution
│   └── linter.py             # AST-based safety checks
├── models/
│   ├── __init__.py           # Package exports
│   └── schemas.py            # Pydantic models
└── utils/
    ├── __init__.py           # Package exports
    └── helpers.py            # Shared utilities
```

---

## 🔒 Security

The executor blocks potentially dangerous imports:

- `os`, `sys`, `subprocess`, `shutil`
- `socket`, `requests`, `urllib`, `http`
- `pickle`, `marshal`, `ctypes`
- `builtins`, `importlib`

Code is executed in an isolated subprocess with strict timeout enforcement.

---

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

---

## 📝 License

MIT License - Feel free to use and modify for your projects.

---

**Built with** ❤️ **using CustomTkinter, LangChain, LangGraph, and Ollama**
