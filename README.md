# Prolog Autonomous Agent

Autonomous Claude agent that integrates Scryer Prolog for logical reasoning and decision-making.

Uses Anthropic's Claude Code SDK with FastMCP server for Prolog execution, enabling logical reasoning on complex problems like banking decisions, puzzles, and rule-based systems.

NOTE: Generarally financial lending are against the terms of service of most commercial LLMs, primarily using the examples as an example of using prolog inside an LLM due to the ability to formulate more compelx logic in it.

## Prerequisites

```bash
# Install Scryer Prolog
cargo install scryer-prolog

# Install uv for Python
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Setup

```bash
# Install project
uv sync

# Set your Anthropic API key
export ANTHROPIC_API_KEY="your-key-here"
```

## Usage

### Basic Usage
```bash
# Run with interactive problem input
uv run prolog-agent

# Run with problem from file
uv run prolog-agent --problem-file loan_scenario.txt

# Load existing Prolog rules
uv run prolog-agent --input bank_loan_rules.pro

# Save generated code and audit trail
uv run prolog-agent --save --output results.txt
```

### Banking Example
```bash
# Evaluate loan application using prebuilt banking rules
uv run prolog-agent --input bank_loan_rules.pro --problem-file loan_scenario.txt
```

The system will:
1. Load banking rules from `bank_loan_rules.pro` 
2. Read the problem statement and applicant data from `loan_scenario.txt`
3. Use Prolog to determine approval decision, risk category, and interest rate

## How It Works

1. **Problem Input**: Claude reads problem statement (scenario + data)
2. **Rule Application**: System applies pure logical rules (no embedded data)
3. **Prolog Execution**: FastMCP server executes Scryer Prolog queries
4. **Decision Making**: Prolog returns logical conclusions
5. **Result Output**: Claude formats the final decision with reasoning

## Key Features

- **Pure Logic Separation**: Rules contain only logic, data comes from problem files
- **Arithmetic Support**: Handles complex calculations (loan-to-value ratios, etc.)
- **Timeout Handling**: Robust execution with proper error handling
- **File Management**: Saves code and audit trails for analysis
- **Banking Rules**: Pre-built loan approval decision system

## File Structure

- `prolog_agent/main.py` - Main Claude agent
- `prolog_agent/prolog_mcp_server.py` - FastMCP server for Prolog execution
- `bank_loan_rules.pro` - Banking decision rules (example)
- `loan_scenario.txt` - Problem statement with applicant data (example) 