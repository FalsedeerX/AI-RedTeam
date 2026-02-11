import operator
from typing import Literal, TypedDict, Annotated, List, Dict
from langchain_ollama import ChatOllama
from langchain_core.messages import AnyMessage, SystemMessage, ToolMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from .config import config
from .tools import retrieve_context, execute_nmap_scan

# Define state
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int

class RedTeamAgent:
    """
    Encapsulates the Red Team Agent graph logic, models, and tools.
    """
    def __init__(self):
        self._init_tools()
        self._init_models()
        self.app = self._build_graph()

    def _init_tools(self):
        self.tools = [retrieve_context, execute_nmap_scan]
        self.tools_by_name = {tool.name: tool for tool in self.tools}

    def _init_models(self):
        base_model = ChatOllama(
            model=config.LLM_MODEL_NAME,
            temperature=0,
            num_ctx=8192,
            base_url=config.LLM_BASE_URL
        )
        self.model = base_model.bind_tools(self.tools)
        
        # Critic uses the same model base but we might want a fresh instance or same
        # keeping it separate for clarity or differing configs later
        self.critic_model = ChatOllama(
            model=config.LLM_MODEL_NAME,
            temperature=0,
            num_ctx=8192,
            base_url=config.LLM_BASE_URL
        )

    # --- Nodes ---

    def llm_call(self, state: MessagesState):
        """LLM decides whether to call a tool or not"""
        return {
            "messages": [
                self.model.invoke(
                    [
                        SystemMessage(
                            content=config.LLM_SYSTEM_PROMPT
                        )
                    ]
                    + state["messages"]
                )
            ],
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

        # Find if there's an Nmap tool call to inspect
        nmap_call = next((tc for tc in last_ai_message.tool_calls if tc["name"] == "execute_nmap_scan"), None)
        
        if not nmap_call:
            return {"messages": []} # No command to criticize

        proposed_command = nmap_call["args"].get("command")
        
        if not proposed_command:
             return {"messages": [HumanMessage(content=f"SYSTEM ERROR: The 'execute_nmap_scan' tool requires a 'command' argument containing the full Nmap command string. You provided arguments: {nmap_call['args']}. Please retry with the correct format.")]}
        
        # Retrieve the latest RAG context from message history
        rag_context = ""
        for m in reversed(messages):
            if isinstance(m, ToolMessage) and m.name == "retrieve_context":
                rag_context = m.content
                break

        # Invoke LLM as the Critic
        critic_response = self.critic_model.invoke([
            SystemMessage(content=config.CRITIC_SYSTEM_PROMPT),
            HumanMessage(content=f"DOCUMENTATION CONTEXT:\n{rag_context}\n\nPROPOSED COMMAND: {proposed_command}")
        ])

        # Logic: If not valid, append the feedback to the conversation
        if "VALID" in critic_response.content.upper() and len(critic_response.content.strip()) < 100:
            return {"messages": []} # Pass
        else:
            feedback = f"CRITICISM DETECTED:\n{critic_response.content}\n\nPlease correct the command and try again."
            return {"messages": [HumanMessage(content=feedback)]}

    # --- Conditional Edges ---

    def should_continue(self, state: MessagesState) -> Literal["critic_node", END]:
        messages = state["messages"]
        last_message = messages[-1]

        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "critic_node"
        return END

    def route_after_critic(self, state: MessagesState) -> Literal["llm_call", "tool_node", END]:
        last_message = state["messages"][-1]
        
        if isinstance(last_message, HumanMessage) and "CRITICISM DETECTED" in last_message.content:
            return "llm_call" # Loop back to fix
        
        return "tool_node"


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
        agent_builder = StateGraph(MessagesState)

        # Add nodes
        agent_builder.add_node("llm_call", self.llm_call)
        agent_builder.add_node("tool_node", self.tool_node)
        agent_builder.add_node("critic_node", self.critic_node)

        # Add edges
        agent_builder.add_edge(START, "llm_call")

        agent_builder.add_conditional_edges(
            "llm_call",
            self.should_continue,
            {"critic_node": "critic_node", END: END}
        )

        agent_builder.add_conditional_edges(
            "critic_node",
            self.route_after_critic,
            {"llm_call": "llm_call", "tool_node": "tool_node", END: END}
        )

        agent_builder.add_edge("tool_node", "llm_call")

        return agent_builder.compile()

def get_agent():
    """
    Factory function to get the agent with compiled graph.
    """
    return RedTeamAgent()
