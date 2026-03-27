# backend/agents/base.py
from dataclasses import dataclass, field
from typing import Any, Generator
from datetime import datetime
import anthropic
from anthropic.types import ToolUnionParam

@dataclass
class AgentStep:
    """A record of one think→act→observe cycle. Streamed to the frontend."""
    agent_name: str
    thought: str          # what Claude decided to do
    action: str           # which tool it called
    action_input: dict    # what arguments it passed
    observation: str      # what the tool returned
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BaseAgent:
    def __init__(self, name: str, client: anthropic.Anthropic, memory=None):
        self.name = name
        self.client = client
        self.memory = memory          # shared memory instance from orchestrator
        self.system_prompt: str = ""  # subclasses override this
        self.tools: dict = {}         # subclasses populate this: {"tool_name": callable}
        self.steps: list[AgentStep] = []

    def think(self, messages: list) -> anthropic.types.Message:
        """
        Send the current conversation history to Claude.
        Claude sees: its system prompt, all prior messages, and the tool schemas.
        Returns the raw API response — we inspect stop_reason in run().
        """
        return self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=self.system_prompt,
            tools=self._tool_schemas(),
            messages=messages,
        )

    def act(self, tool_name: str, tool_input: dict) -> str:
        """
        Look up the tool by name and call the Python function.
        Claude never runs code directly — it just says what it wants.
        We do the actual execution here and hand the result back.
        """
        if tool_name not in self.tools:
            return f"Error: unknown tool '{tool_name}'"
        
        try:
            result = self.tools[tool_name](**tool_input)
            return str(result)
        except Exception as e:
            return f"Error running {tool_name}: {str(e)}"

    def run(self, task: str) -> Generator[dict, None, str]:
        """
        The ReAct loop. This is a generator — it yields a status dict
        after each step so the orchestrator can stream progress to React.

        Yields:  { "agent": name, "action": ..., "observation": ... }
        Returns: the final text answer (via StopIteration.value)
        """
        self.steps = []   # reset for this run
        messages = [{"role": "user", "content": task}]

        for iteration in range(10):  # hard cap — prevents infinite loops

            response = self.think(messages)

            # --- Claude is done reasoning, has a final answer ---
            if response.stop_reason == "end_turn":
                final = next(
                    (block.text for block in response.content if hasattr(block, "text")),
                    "No response."
                )
                return final

            # --- Claude wants to use a tool ---
            tool_use_block = next(
                (block for block in response.content if block.type == "tool_use"),
                None
            )

            if not tool_use_block:
                # Shouldn't happen, but handle gracefully
                return "Agent stopped unexpectedly."

            tool_name  = tool_use_block.name
            tool_input = tool_use_block.input

            # Execute the tool
            observation = self.act(tool_name, tool_input)

            # Record the step
            step = AgentStep(
                agent_name=self.name,
                thought=f"Calling {tool_name}",
                action=tool_name,
                action_input=tool_input,
                observation=observation,
            )
            self.steps.append(step)

            # Yield progress to the orchestrator so it can stream to React
            yield {
                "agent":       self.name,
                "iteration":   iteration + 1,
                "action":      tool_name,
                "input":       tool_input,
                "observation": observation[:300],  # truncate for the UI
            }

            # Append both sides of the tool exchange to the message history.
            # Claude needs to see its own tool_use block AND the result
            # together, otherwise the API returns a validation error.
            messages += [
                {"role": "assistant", "content": response.content},
                {
                    "role": "user",
                    "content": [{
                        "type":        "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content":     observation,
                    }]
                }
            ]

        return "Max iterations reached without a final answer."

    def _tool_schemas(self) -> list[ToolUnionParam]:
        """
        Return the Anthropic-format tool definitions for this agent.
        Subclasses define these — BaseAgent doesn't know what tools exist.
        """
        raise NotImplementedError("Subclasses must implement _tool_schemas()")
