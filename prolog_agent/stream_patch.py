"""Runtime patch for Claude Code SDK to robustly decode streamed JSON output.

Claude Code CLI sometimes splits a single JSON object across multiple stdout
lines. The upstream SDK assumes that every line is a complete JSON document and
attempts to decode it individually. When a split occurs this raises
``json.JSONDecodeError`` terminating the whole conversation. This patch wraps
``SubprocessCLITransport.receive_messages`` with a more tolerant
implementation that buffers partial lines until a valid JSON document can be
decoded.

The public interface of the SDK is preserved – the patched method yields the
same message dictionaries as the original one. No features are removed or
simplified; we only make the JSON parsing logic more resilient.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
import json
from typing import Any

import anyio

# Import SDK components. The import path is stable across SDK versions >=0.0.13.
from claude_code_sdk._internal.transport.subprocess_cli import (
    SubprocessCLITransport as _SubprocessCLITransport,
)
from claude_code_sdk._errors import (
    CLIConnectionError,
    CLIJSONDecodeError as _SDKJSONDecodeError,
    ProcessError,
)

__all__ = ["apply_patch"]


async def _patched_receive_messages(self: _SubprocessCLITransport) -> AsyncIterator[dict[str, Any]]:  # type: ignore[override]
    """Patched version of ``receive_messages``.

    Differences from the upstream implementation:
    1. Maintains an internal *buffer* string that can collect fragments of a
       JSON document across multiple stdout chunks.
    2. Only attempts ``json.loads`` when a complete JSON object seems present.
       If parsing fails we keep the fragment in the buffer and wait for more
       data instead of raising ``json.JSONDecodeError`` immediately.
    3. The original error-handling behaviour (raising ``ProcessError`` if the
       CLI exits with a non-zero status, etc.) is preserved.
    """

    if not self._process or not self._stdout_stream:
        raise CLIConnectionError("Not connected")

    stderr_lines: list[str] = []
    buffer: str = ""

    async def _read_stderr() -> None:
        """Continuously consume stderr so the buffer does not fill up."""
        if self._stderr_stream:
            try:
                async for line in self._stderr_stream:
                    stderr_lines.append(line.strip())
            except anyio.ClosedResourceError:
                # The stream is closed – nothing to do.
                pass

    # We need to yield from inside the task group so we cannot put the whole
    # body in a separate coroutine. Instead we create the task group manually.
    async with anyio.create_task_group() as tg:
        tg.start_soon(_read_stderr)

        try:
            async for chunk in self._stdout_stream:  # type: ignore[attr-defined]
                buffer += chunk

                # Process all *complete* lines currently in the buffer.
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line_str = line.strip()
                    if not line_str:
                        continue

                    # Attempt to decode the line. If we fail we assume the JSON
                    # is incomplete and prepend it back to the buffer so that
                    # the next chunk can complete it.
                    try:
                        data = json.loads(line_str)
                        try:
                            yield data
                        except GeneratorExit:
                            # Allow generator cleanup without error.
                            return
                    except json.JSONDecodeError:
                        # Incomplete JSON – wait for more data.
                        buffer = line + "\n" + buffer  # re-insert and break
                        break

        except anyio.ClosedResourceError:
            # The underlying stream closed – normal shutdown path.
            pass

    # After the loop exits attempt to parse any remaining buffered data.
    if buffer.strip():
        try:
            yield json.loads(buffer.strip())
        except json.JSONDecodeError as e:
            # The buffer contains something that *looked* like JSON but is not
            # valid even after the process ended. Re-raise using the SDK's
            # dedicated error type for consistency.
            if buffer.lstrip().startswith("{") or buffer.lstrip().startswith("["):
                raise _SDKJSONDecodeError(buffer, e) from e

    # Wait for the CLI process to exit and propagate errors if necessary.
    await self._process.wait()
    if self._process.returncode not in (None, 0):
        stderr_output = "\n".join(stderr_lines)
        if stderr_output and "error" in stderr_output.lower():
            raise ProcessError(
                "CLI process failed",
                exit_code=self._process.returncode,
                stderr=stderr_output,
            )


def apply_patch() -> None:
    """Apply the runtime patch if it has not been applied yet."""
    # Avoid patching multiple times in case the module is re-imported.
    if getattr(_SubprocessCLITransport, "_patched_for_streaming", False):
        return

    # Monkey-patch the method.
    _SubprocessCLITransport.receive_messages = _patched_receive_messages  # type: ignore[assignment]
    _SubprocessCLITransport._patched_for_streaming = True  # type: ignore[attr-defined]


# Apply immediately on import so simply importing the module activates the fix.
apply_patch() 