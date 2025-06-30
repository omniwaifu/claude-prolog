#!/usr/bin/env python3
"""FastMCP server for Scryer Prolog execution."""

import subprocess
import tempfile
import os
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# Initialize FastMCP
mcp = FastMCP("Scryer Prolog")

class Scryer:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.scryer_path = self._find_scryer()
    
    def _find_scryer(self) -> str:
        """Find scryer-prolog executable."""
        candidates = [
            "scryer-prolog",
            str(Path.home() / ".cargo" / "bin" / "scryer-prolog"),
            "/usr/local/bin/scryer-prolog",
            "/usr/bin/scryer-prolog"
        ]
        
        for path in candidates:
            try:
                result = subprocess.run(
                    [path, "--version"], 
                    capture_output=True, 
                    timeout=2,
                    text=True
                )
                if result.returncode == 0:
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        
        raise RuntimeError("Scryer Prolog not found. Install with: cargo install scryer-prolog")
    
    def execute(self, prolog_code: str, query: str) -> dict[str, Any]:
        """Execute Prolog code with query in memory."""
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".pro", delete=False) as tmp:
                # Write clean Prolog code
                clean_code = prolog_code.strip()
                lines = []
                for line in clean_code.split('\n'):
                    line = line.strip()
                    if line and not line.startswith(':-') and not line.startswith('?-'):
                        lines.append(line)
                
                tmp.write('\n'.join(lines) + '\n')
                tmp_path = tmp.name

            # Execute with goal - use once/1 to prevent backtracking issues
            goal = f"once(({query} -> write('TRUE') ; write('FALSE'))), halt"
            
            result = subprocess.run(
                [self.scryer_path, tmp_path, "-g", goal],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            # Clean up
            os.unlink(tmp_path)

            return {
                "success": result.returncode == 0,
                "query": query,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "query": query,
                "stdout": "",
                "stderr": f"Query timed out after {self.timeout} seconds",
                "returncode": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "stdout": "",
                "stderr": f"Execution error: {str(e)}",
                "returncode": -1,
            }

# Global scryer instance
scryer = Scryer()

@mcp.tool()
def prolog_query(facts_and_rules: str, query: str) -> str:
    """Execute Prolog code with a query for logical reasoning.
    
    Args:
        facts_and_rules: Prolog facts and rules (e.g., 'fact(a, b). rule(X,Z) :- fact(X,Y), fact(Y,Z).')
        query: Prolog query to execute (e.g., 'rule(a, c)')
    
    Returns:
        The result of the Prolog query execution
    """
    if not facts_and_rules or not query:
        return "Error: Both 'facts_and_rules' and 'query' are required"
    
    result = scryer.execute(facts_and_rules, query)
    
    if result["success"]:
        output = result["stdout"] or "TRUE"
        return f"Query: {query}\nResult: SUCCESS\nOutput: {output}"
    else:
        return f"Query: {query}\nResult: FAILED\nError: {result['stderr']}"

if __name__ == "__main__":
    mcp.run() 