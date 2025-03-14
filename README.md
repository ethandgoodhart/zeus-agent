# 🚀 zeus-agent

Ultra-low latency LLM computer agent using Accessibility APIs. Control your Mac with any LLM.

<br/><div align="center">

![Zeus Demo](zeus.gif)
<br/><sub>✨ actual speed (not sped up) ✨</sub>

</div>

## 🔥 features

- 🧠 Intelligent task planning and execution
- ⚡ Lightning-fast response time
- 🖥️ Native macOS integration via Accessibility APIs
- 🔄 Real-time DOM analysis of applications
- 🧑‍💻 Claude Code integration for coding tasks

## 🚀 Getting Started
### Install

```bash
pip install -r requirements.txt
```

### Running

```bash
python agent.py
```

### Prerequisites

- macOS (10.15+)
- Python 3.8+
- Gemini API key
- Claude CLI installed (for coding tasks)

## 🔧 Setting Up Claude Code CLI

Claude Code is Anthropic's command-line interface for coding assistance. Follow these steps to set it up:

### Installation

1. **Install Claude Code CLI**:
   ```bash
   pip install claude-cli
   ```

2. **Log in to your Anthropic account**:
   ```bash
   claude login
   ```
   This will open a browser window to authenticate with your Anthropic account.

3. **Verify the installation**:
   ```bash
   claude --version
   ```

### Usage

- **Simple query mode**:
  ```bash
  claude -p "Write a function to calculate prime numbers"
  ```

- **Interactive mode** (for file operations):
  ```bash
  claude
  ```
  Then follow the prompts to enter your coding requests.

### Troubleshooting

- If you encounter permission errors, make sure to run:
  ```bash
  chmod +x $(which claude)
  ```

- If Claude Code CLI is not found in your PATH, add the pip installation directory to your PATH:
  ```bash
  export PATH="$HOME/.local/bin:$PATH"
  ```

### Additional Resources

- [Claude Code CLI Documentation](https://docs.anthropic.com/claude/cli)
- [Claude API Documentation](https://docs.anthropic.com/claude/docs)

## 🧑‍💻 Using Claude Code Integration

Zeus can now use Claude Code for coding-related tasks. When you input a query related to coding (like reading files, writing code, or editing files), Zeus will automatically use Claude Code to handle the request.

### Usage Patterns

There are multiple ways to use the Claude Code integration:

1. **Direct prefix**: Start your command with `claude:` to explicitly use Claude Code
   - Example: `claude: write a Python script to calculate factorials`

2. **Automatic detection**: The agent will automatically detect coding-related queries
   - Example: `create a new file called test.py`

3. **Directory specification**: You can specify a directory for Claude to work in
   - Example: `claude: in /path/to/project: list all JavaScript files`

### Command Types

The integration automatically handles two types of commands:

- **Simple queries**: For tasks that don't require file operations (uses `claude -p`)
- **Complex file operations**: For tasks that need to create, read, or modify files (uses interactive mode)

The system automatically handles permission prompts and other interactions needed when working with files.

### Examples

- `claude: create a new file hello.py with a hello world function`
- `claude: in ~/projects: fix the bugs in main.js`
- `write a React component for a login form`
- `claude: explain what this code does: [paste code here]`

Make sure you have the Claude CLI installed and configured on your system.
