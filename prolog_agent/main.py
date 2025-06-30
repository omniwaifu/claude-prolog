"""Main entry point for Prolog Autonomous Agent."""

from typing import Optional
import os

import anyio
import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from claude_code_sdk import query as claude_query, ClaudeCodeOptions
from claude_code_sdk.types import AssistantMessage, ToolUseBlock, TextBlock, UserMessage
from prolog_agent import stream_patch  # Activates runtime patch for Claude Code SDK  # noqa: F401

app = typer.Typer(help="Prolog Autonomous Agent using Claude Code SDK")
console = Console()


class PrologAgent:
    """Autonomous Claude agent with Prolog reasoning capabilities."""
    
    def __init__(self):
        self.conversation_history = []
        self.audit_log = []
        self.generated_prolog = None
    
    def _extract_queries_from_content(self, content: str) -> list[str]:
        """Extract potential queries from Prolog content."""
        # Look for predicates defined in the content and create basic queries
        predicates = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('%') and '(' in line:
                # Extract predicate name from facts/rules
                if line.endswith('.') or ':-' in line:
                    pred_part = line.split('(')[0].strip()
                    if ':-' in pred_part:
                        continue  # Skip rule heads for now
                    if pred_part and pred_part not in predicates:
                        predicates.append(pred_part)
        
        # Generate basic queries for each predicate found
        queries = []
        for pred in predicates:
            # Create a simple query like predicate(X, Y)
            queries.append(f"{pred}(_, _)")
        
        # If no predicates found, return a default query
        if not queries:
            queries.append("true")
            
        return queries
    
    def load_prolog_file(self, filepath: str) -> str:
        """Load Prolog code from file."""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            self.audit_log.append(f"Loaded Prolog from: {filepath}")
            return content
        except FileNotFoundError:
            self.audit_log.append(f"ERROR: File not found: {filepath}")
            raise
        except Exception as e:
            self.audit_log.append(f"ERROR loading file {filepath}: {str(e)}")
            raise
    
    def save_prolog_file(self, content: str, filename: Optional[str] = None) -> str:
        """Save Prolog code to file."""
        if filename is None:
            # Generate filename from problem or timestamp
            import time
            timestamp = int(time.time())
            filename = f"problem_{timestamp}.pl"
        
        try:
            with open(filename, 'w') as f:
                f.write(content)
            self.audit_log.append(f"Saved Prolog to: {filename}")
            return filename
        except Exception as e:
            self.audit_log.append(f"ERROR saving to {filename}: {str(e)}")
            raise
    
    def save_audit_log(self, filepath: str, problem: str, result: str):
        """Save complete audit trail to file."""
        try:
            with open(filepath, 'w') as f:
                f.write("PROLOG REASONING AUDIT LOG\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Problem: {problem}\n\n")
                f.write("Generated Prolog Code:\n")
                f.write("-" * 30 + "\n")
                if self.generated_prolog:
                    f.write(self.generated_prolog + "\n")
                f.write("-" * 30 + "\n\n")
                f.write("Audit Trail:\n")
                for entry in self.audit_log:
                    f.write(f"- {entry}\n")
                f.write(f"\nFinal Result: {result}\n")
            console.print(f"Audit log saved to: {filepath}")
        except Exception as e:
            console.print(f"Error saving audit log: {str(e)}")
    
    async def solve_problem(self, problem: str, max_turns: int = 10, input_file: Optional[str] = None, save_prolog: bool = False, output_file: Optional[str] = None) -> None:
        """Solve a problem using autonomous Claude with Prolog tools."""
        
        console.print(Panel(
            Text(f"Problem: {problem}", style="bold blue"),
            title="Prolog Autonomous Agent",
            border_style="blue"
        ))
        
        self.audit_log.append(f"Starting problem: {problem}")
        
        # Handle input file if provided
        if input_file:
            try:
                prolog_content = self.load_prolog_file(input_file)
                self.generated_prolog = prolog_content
                console.print(Panel(
                    f"Using existing Prolog file: {input_file}",
                    title="Input File Loaded",
                    border_style="cyan"
                ))
                
                # Modified system prompt for pre-loaded Prolog
                system_prompt = (
                    "You have been provided with pre-written Prolog rules. "
                    "Your task is to use the mcp__scryer-prolog__prolog_query tool with these rules. "
                    "DO NOT try to read files or generate new Prolog code. "
                    "Extract the applicant data from the problem statement, then use the prolog_query tool "
                    "with the provided rules and the extracted facts to make decisions. "
                    
                    "PROCESS: "
                    "1. Read the problem statement and extract applicant facts "
                    "2. Use mcp__scryer-prolog__prolog_query tool with: "
                    "   - facts_and_rules: The provided Prolog rules + extracted applicant facts "
                    "   - query: The specific query to test (e.g., 'approve_loan(applicant_name)') "
                    "3. Report the result based on Prolog output "
                    
                    f"PROLOG RULES TO USE:\n{prolog_content}\n"
                    "Use these exact rules with the applicant data from the problem statement."
                )
            except Exception as e:
                console.print(f"Error loading input file: {str(e)}")
                return
        else:
            # System prompt with guard-rails for logical reasoning
            system_prompt = (
                "You are a logical reasoning agent that uses Prolog to solve problems with built-in error checking. "
                
                "MANDATORY PREMISE SANITY PASS: "
                "Before doing anything else, restate the key assumptions from the problem in bullet form. "
                "Flag anything that contradicts ordinary world knowledge or contains internal contradictions. "
                "If contradictions exist, ask the user to clarify instead of proceeding. "
                
                "PROCESS WITH SELF-CRITIQUE: "
                "1. Extract ONLY explicit facts from the problem statement "
                "2. Create simple Prolog facts (no complex rules unless necessary) "
                "3. Use prolog_query tool to test your hypothesis "
                "4. SELF-CRITIQUE: Review your Prolog code for logical gaps or premise errors "
                "5. If critique finds issues, regenerate the Prolog code "
                "6. Report final result based ONLY on prolog_query output "
                
                "ERROR DETECTION: "
                "- If any noun has implausible attributes, treat as potential trick "
                "- If prolog_query returns SUCCESS/TRUE, answer YES "
                "- If prolog_query returns FAILED/FALSE, answer NO "
                "- Never override Prolog results with manual reasoning "
                
                "Keep Prolog code minimal and literal. No assumptions beyond what's stated."
            )
        
        # Configure Claude with ONLY the MCP server for Prolog execution
        current_dir = os.path.dirname(os.path.abspath(__file__))
        server_path = os.path.join(current_dir, "prolog_mcp_server.py")
        
        options = ClaudeCodeOptions(
            system_prompt=system_prompt,
            max_turns=max_turns,
            permission_mode='acceptEdits',
            allowed_tools=["mcp__scryer-prolog__prolog_query"],
            max_thinking_tokens=0,
            mcp_servers={
                "scryer-prolog": {
                    "command": "uv",
                    "args": ["run", "python", server_path],
                    "env": {}
                }
            }
        )
        
        # Start the autonomous conversation
        prompt = f"Solve this problem using Prolog reasoning: {problem}"

        turn_count = 0
        
        async for message in claude_query(prompt=prompt, options=options):
            turn_count += 1
            console.print(f"\n--- Turn {turn_count} ---")
            
            if isinstance(message, AssistantMessage):
                # Display Claude's response
                for block in message.content:
                    if isinstance(block, TextBlock):
                        console.print(Panel(
                            block.text,
                            title=f"Claude (Turn {turn_count})",
                            border_style="green"
                        ))
                    
                    elif isinstance(block, ToolUseBlock):
                        console.print(Panel(
                            f"Tool Call: {block.name}\nInput: {block.input}",
                            title=f"Tool Use (Turn {turn_count})",
                            border_style="yellow"
                        ))
                        
                        # Capture Prolog code from prolog_query tool calls
                        if (block.name == "mcp__scryer-prolog__prolog_query" and 
                            isinstance(block.input, dict)):
                            
                            facts_and_rules = block.input.get("facts_and_rules", "")
                            query = block.input.get("query", "")
                            
                            if facts_and_rules and not input_file:  # Only capture if not using input file
                                self.generated_prolog = facts_and_rules
                                self.audit_log.append(f"Generated Prolog code: {len(facts_and_rules)} characters")
                                self.audit_log.append(f"Query: {query}")
                        
                        # If Claude writes a .pro file, note it
                        if (block.name == "Write" and 
                            isinstance(block.input, dict) and
                            str(block.input.get("file_path", "")).endswith(".pro")):
                            
                            console.print(Panel(
                                f"Prolog file created: {block.input.get('file_path', 'unknown')}",
                                title="Prolog File Created",
                                border_style="cyan"
                            ))
            
            elif isinstance(message, UserMessage):
                # Handle user messages (tool results)
                if hasattr(message, 'content') and message.content:
                    console.print(Panel(
                        str(message.content),
                        title=f"Tool Result (Turn {turn_count})",
                        border_style="cyan"
                    ))
        
        console.print(Panel(
            f"Conversation completed in {turn_count} turns",
            title="Summary",
            border_style="magenta"
        ))
        
        # Handle saving options
        final_result = "See conversation above"  # Could be enhanced to extract actual result
        
        if save_prolog and self.generated_prolog:
            try:
                saved_file = self.save_prolog_file(self.generated_prolog)
                console.print(Panel(
                    f"Prolog code saved to: {saved_file}",
                    title="Saved Prolog",
                    border_style="green"
                ))
            except Exception as e:
                console.print(f"Error saving Prolog file: {str(e)}")
        
        if output_file:
            self.save_audit_log(output_file, problem, final_result)


@app.command()
def solve(
    problem: Optional[str] = typer.Option(
        None, 
        "--problem", 
        "-p",
        help="Problem to solve"
    ),
    max_turns: int = typer.Option(
        10,
        "--max-turns",
        "-t", 
        help="Maximum conversation turns"
    ),
    input_file: Optional[str] = typer.Option(
        None,
        "--input",
        "-i",
        help="Use existing Prolog file instead of generating one"
    ),
    save_prolog: bool = typer.Option(
        False,
        "--save",
        "-s",
        help="Save generated Prolog code to file"
    ),
    output_file: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Save audit trace and results to file"
    ),
    problem_file: Optional[str] = typer.Option(
        None,
        "--problem-file",
        "-f",
        help="Load problem statement from text file"
    )
):
    """Solve a logical problem using autonomous Claude with Prolog reasoning."""
    
    # Load problem from file if specified
    if problem_file:
        try:
            with open(problem_file, 'r') as f:
                problem = f.read().strip()
            console.print(f"Loaded problem from: {problem_file}")
        except Exception as e:
            console.print(f"Error loading problem file: {str(e)}")
            return
    
    if not problem:
        console.print("Error: Problem is required. Use --problem or --problem-file to specify a problem to solve.")
        return
    
    agent = PrologAgent()
    anyio.run(agent.solve_problem, problem, max_turns, input_file, save_prolog, output_file)





if __name__ == "__main__":
    app() 