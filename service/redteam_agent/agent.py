import operator
import re
from typing import Literal, TypedDict, Annotated, List, Dict
from langchain_ollama import ChatOllama
from langchain_core.messages import AnyMessage, SystemMessage, ToolMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from .config import config
from .tools import retrieve_context, execute_nmap_scan, execute_msf_module

VALID_PHASES = ("recon", "enumeration", "exploitation", "complete")

# Define state
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int
    current_phase: str
    plan: str

class RedTeamAgent:
    """
    Encapsulates the Red Team Agent graph logic, models, and tools.

    Graph flow:
        START -> planner -> tactician -> critic_node -> tool_node -> planner
    The Planner decides *what* to do (phase + directive).
    The Tactician decides *how* to do it (tool calls).
    The Critic validates proposed commands before execution.
    """
    def __init__(self):
        self._init_tools()
        self._init_models()
        self.app = self._build_graph()

    def _init_tools(self):
        self.tools = [retrieve_context, execute_nmap_scan, execute_msf_module]
        self.tools_by_name = {tool.name: tool for tool in self.tools}

    def _init_models(self):
        base_model = ChatOllama(
            model=config.LLM_MODEL_NAME,
            temperature=0,
            num_ctx=8192,
            base_url=config.LLM_BASE_URL
        )
        self.tactician_model = base_model.bind_tools(self.tools)
        self.planner_model = ChatOllama(
            model=config.LLM_MODEL_NAME,
            temperature=0,
            num_ctx=8192,
            base_url=config.LLM_BASE_URL
        )
        self.critic_model = ChatOllama(
            model=config.LLM_MODEL_NAME,
            temperature=0,
            num_ctx=8192,
            base_url=config.LLM_BASE_URL
        )

    # --- Nodes ---

    def planner_node(self, state: MessagesState):
        """Planner: decides the current engagement phase and issues a directive.

        Analyses the full message history (tool outputs, findings, etc.) and
        returns a structured PHASE + DIRECTIVE that the Tactician will execute.
        """
        response = self.planner_model.invoke(
            [SystemMessage(content=config.PLANNER_SYSTEM_PROMPT)]
            + state["messages"]
        )
        text = response.content.strip()
        phase = state.get("current_phase", "recon")
        directive = text  # Fallback: treat the whole response as the directive

        phase_match = re.search(r"PHASE:\s*(recon|enumeration|exploitation|complete)", text, re.IGNORECASE)
        directive_match = re.search(r"DIRECTIVE:\s*(.+)", text, re.DOTALL)

        if phase_match:
            phase = phase_match.group(1).lower()
        if directive_match:
            directive = directive_match.group(1).strip()

        planner_message = HumanMessage(
            content=f"[PLANNER — phase: {phase}]\n{directive}"
        )

        return {
            "messages": [planner_message],
            "current_phase": phase,
            "plan": directive,
        }

    def tactician_node(self, state: MessagesState):
        """Tactician: generates specific tool calls based on the Planner's directive.

        Focuses *only* on execution — strategy is left to the Planner.
        """
        directive = state.get("plan", "")

        # Prepend the directive so the Tactician knows exactly what to do
        directive_preamble = (
            f"CURRENT PHASE: {state.get('current_phase', 'recon')}\n"
            f"PLANNER DIRECTIVE: {directive}\n\n"
            "Generate the appropriate tool call(s) to carry out the above directive."
        )
        return {
            "messages": [ self.tactician_model.invoke(
                [
                    SystemMessage(content=config.TACTICIAN_SYSTEM_PROMPT),
                    HumanMessage(content=directive_preamble)
                ]
                + state["messages"]
            )],
            "llm_calls": state.get('llm_calls', 0) + 1
        }

    def tool_node(self, state: MessagesState):
        """Performs the tool call"""
        result = []
        last_message = state["messages"][-1]
        
        if not hasattr(last_message, 'tool_calls'):
            return {"messages": []}

        for tool_call in last_message.tool_calls:
            tool = self.tools_by_name[tool_call["name"]]
            observation = tool.invoke(tool_call["args"])
            
            # Handle potential artifact return (content, artifact)
            content = observation
            if isinstance(observation, tuple):
                content = observation[0]
            
            result.append(ToolMessage(
                content=str(content), 
                tool_call_id=tool_call["id"], 
                name=tool_call["name"]
            ))
        return {"messages": result}

    def critic_node(self, state: MessagesState):
        """LLM Critic inspects proposed commands against RAG context"""
        messages = state["messages"]
        last_ai_message = messages[-1]

        if not hasattr(last_ai_message, "tool_calls") or not last_ai_message.tool_calls:
            return {"messages": []}

        # Find if there's an Nmap tool call to inspect
        nmap_call = next((tc for tc in last_ai_message.tool_calls if tc["name"] == "execute_nmap_scan"), None)
        
        if not nmap_call:
            return {"messages": []} # No command to criticize

        proposed_command = nmap_call["args"].get("command")
        
        if not proposed_command:
            return {"messages": [HumanMessage(content=(
                f"SYSTEM ERROR: The 'execute_nmap_scan' tool requires a 'command' "
                f"argument containing the full Nmap command string. You provided "
                f"arguments: {nmap_call['args']}. Please retry with the correct format."
            ))]}

        # Retrieve the latest RAG context from message history
        rag_context = ""
        for m in reversed(messages):
            if isinstance(m, ToolMessage) and m.name == "retrieve_context":
                rag_context = m.content
                break

        # Invoke LLM as the Critic
        critic_response = self.critic_model.invoke([
            SystemMessage(content=config.CRITIC_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"DOCUMENTATION CONTEXT:\n{rag_context}\n\n"
                f"PROPOSED COMMAND: {proposed_command}"
            ))
        ])

        # Logic: If not valid, append the feedback to the conversation
        if "VALID" in critic_response.content.upper() and len(critic_response.content.strip()) < 100:
            return {"messages": []} # Pass
        else:
            feedback = (
                f"CRITICISM DETECTED:\n{critic_response.content}\n\n"
                "Please correct the command and try again."
            )
            return {"messages": [HumanMessage(content=feedback)]}

    # --- Conditional Edges ---

    def route_after_planner(self, state: MessagesState) -> Literal["tactician", "__end__"]:
        """After the Planner runs, decide whether to continue or finish."""
        phase = state.get("current_phase", "recon")
        if phase == "complete":
            return END
        return "tactician"

    def route_after_tactician(self, state: MessagesState) -> Literal["critic_node", END]:
        """After the Tactician runs, check if there are tool calls to review."""
        messages = state["messages"]
        last_message = messages[-1]

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "critic_node"
        return END

    def route_after_critic(self, state: MessagesState) -> Literal["tactician", "tool_node", END]:
        """After the Critic runs, either loop back to fix or proceed to execute."""
        last_message = state["messages"][-1]
        
        if isinstance(last_message, HumanMessage) and "CRITICISM DETECTED" in last_message.content:
            return "tactician"  # Loop back to fix
        
        return "tool_node"

    # --- Utilities ---

    def save_graph_image(self, file_path="graph.png"):
        """Generate and save the graph structure as an image."""
        try:
            graph_png = self.app.get_graph(xray=True).draw_mermaid_png()
            with open(file_path, "wb") as f:
                f.write(graph_png)
            print(f"Graph image saved to '{file_path}'")
        except Exception as e:
            print(f"Could not save graph image: {e}")

    # --- Graph Construction ---

    def _build_graph(self):
        """Build the StateGraph: START -> planner -> tactician -> critic -> tool_node -> planner."""
        agent_builder = StateGraph(MessagesState)

        # Add nodes
        agent_builder.add_node("planner", self.planner_node)
        agent_builder.add_node("tactician", self.tactician_node)
        agent_builder.add_node("tool_node", self.tool_node)
        agent_builder.add_node("critic_node", self.critic_node)

        # Add edges
        
        # Entry point
        agent_builder.add_edge(START, "planner")
        # Planner -> Tactician / END
        agent_builder.add_conditional_edges(
            "planner",
            self.route_after_planner,
            {"tactician": "tactician", END: END},
        )
        # Tactician -> Critic / END
        agent_builder.add_conditional_edges(
            "tactician",
            self.route_after_tactician,
            {"critic_node": "critic_node", END: END},
        )
        # Critic -> Tactician (fix) / tool_node (execute)
        agent_builder.add_conditional_edges(
            "critic_node",
            self.route_after_critic,
            {"tactician": "tactician", "tool_node": "tool_node", END: END},
        )
        # tool_node -> planner
        agent_builder.add_edge("tool_node", "planner")

        return agent_builder.compile()

def get_agent():
    """
    Factory function to get the agent with compiled graph.
    """
    return RedTeamAgent()
