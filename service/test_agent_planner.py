# Manual test script for the Planner → Tactician → Critic architecture (Issue #36)
# Must be run from the 'service' directory, or ensure 'service' is in PYTHONPATH.
# Usage:  cd service && python test_agent_planner.py
#    or:  python service/test_agent_planner.py   (from repo root)

import sys
import os
from langchain_core.messages import HumanMessage
from redteam_agent import ingest_documents, get_agent, config
from redteam_agent.vector_store import clear_vector_store
from langgraph.types import Command

# Ensure stdout/stderr use UTF-8 on all platforms (Windows cp1252, Linux C locale, etc.)
# This prevents UnicodeEncodeError when printing box-drawing chars, emoji, and symbols.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ANSI colours for readability (disable with NO_COLOR=1)
USE_COLOR = os.environ.get("NO_COLOR") is None
def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

CYAN    = lambda t: _c("36", t)
GREEN   = lambda t: _c("32", t)
YELLOW  = lambda t: _c("33", t)
RED     = lambda t: _c("31", t)
MAGENTA = lambda t: _c("35", t)
BLUE    = lambda t: _c("34", t)
BOLD    = lambda t: _c("1", t)


def main():
    print(BOLD("=" * 60))
    print(BOLD("  AI RedTeam Agent — Planner / Tactician Manual Test"))
    print(BOLD("=" * 60))

    print(f"\nConfiguration:")
    print(f"  Embedder : {config.EMBEDDING_MODEL_NAME}")
    print(f"  LLM      : {config.LLM_MODEL_NAME}")
    print(f"  LLM URL  : {config.LLM_BASE_URL}")
    print(f"  ChromaDB : {config.CHROMA_PERSIST_DIRECTORY}")
    print(f"  LangSmith Trace : {'Enabled' if os.getenv('LANGSMITH_TRACING') else 'Disabled'}")

    # Step 1: Document Ingestion
    print(BOLD(f"\n[Step 1] Document Ingestion"))
    print(f"  Source directory: {config.DOCS_SOURCE_DIRECTORY}")
    choice = input("  Ingest documents? (y / n / c=clear+reingest): ").strip().lower()

    if choice == "y":
        try:
            ingest_documents(config.DOCS_SOURCE_DIRECTORY)
        except Exception as e:
            print(RED(f"  Ingestion failed: {e}"))
            return
    elif choice == "c":
        print("  Clearing vector store...")
        clear_vector_store()
        print("  Re-ingesting documents...")
        ingest_documents(config.DOCS_SOURCE_DIRECTORY)
    else:
        print("  Skipped.")

    # Step 2: Build the Agent Graph
    print(BOLD("\n[Step 2] Build Agent Graph"))
    print("  Please ensure Ollama is running (ollama serve).\n")

    try:
        agent = get_agent()
        graph = agent.app
        print(GREEN("  ✓ Agent graph compiled successfully."))
    except Exception as e:
        print(RED(f"  ✗ Failed to build agent: {e}"))
        return

    # Save graph image
    img_path = "agent_graph_planner.png"
    agent.save_graph_image(img_path)
    print(f"  Graph image saved → {img_path}")

    # Step 3: Run Query
    print(BOLD("\n[Step 3] Run Query"))

    default_query = "Perform a penetration test against 127.0.0.1"
    query = input(f"  Enter prompt (press Enter for default):\n  > ").strip()
    if not query:
        query = default_query

    print(f"\n  Query: {query}")
    print("─" * 60)

    initial_state = {
        "messages": [HumanMessage(content=query)],
        "llm_calls": 0,
        "current_phase": "recon",
        "plan": "",
        "findings": [],
        "phase_history": [],
    }
    config_run = {"configurable": {"thread_id": "test-1"}, "recursion_limit": 100}

    try:
        phase_history = []
        step = 0
        current_input = initial_state
        interrupted = True
        while interrupted:
            interrupted = False
            for event in graph.stream(current_input, config=config_run):
                # ── Human-in-the-loop: interrupt detected ──
                if "__interrupt__" in event:
                    payload = event["__interrupt__"][0].value
                    actions = payload.get('proposed_actions', [])
                    actions_str = "\n".join(
                        f"    [{tc['name']}] {reason}" for tc, reason in actions
                    ) if actions else "    (none)"
                    print((
                        f"\n{'═'*60}\n"
                        f"{RED(BOLD('  ⚠  AGENT REQUESTING OPERATOR APPROVAL'))}\n"
                        f"{'═'*60}\n"
                        f"  Risk level : {payload.get('risk_level', 'HIGH')}\n"
                        f"  Actions    :\n{actions_str}\n"
                        f"{'─'*60}\n"
                    ))
                    response = input("  Approve? (yes / no): ").strip().lower()
                    current_input = Command(resume=response in ("yes", "y", "approve"))
                    interrupted = True
                    break

                for node_name, values in event.items():
                    step += 1

                    # ── Header ──
                    if node_name == "planner":
                        label = MAGENTA(f"★ PLANNER (step {step})")
                    elif node_name == "tactician":
                        label = CYAN(f"⚙ TACTICIAN (step {step})")
                    elif node_name == "critic_node":
                        label = YELLOW(f"✎ CRITIC (step {step})")
                    elif node_name == "risk_gate_node":
                        label = RED(f"🛡 RISK GATE (step {step})")
                    elif node_name == "tool_node":
                        label = GREEN(f"▶ TOOL (step {step})")
                    elif node_name == "analyst_node":
                        label = BLUE(f"📊 ANALYST (step {step})")
                    else:
                        label = f"  {node_name} (step {step})"

                    print(f"\n{'─'*60}")
                    print(f"  {label}")
                    print(f"{'─'*60}")

                    # ── Phase / Plan ──
                    if "current_phase" in values:
                        phase = values["current_phase"]
                        phase_history.append(phase)
                        print(f"  Phase : {BOLD(phase.upper())}")

                    if "plan" in values and values["plan"]:
                        plan_text = values["plan"]
                        if len(plan_text) > 300:
                            plan_text = plan_text[:300] + " ..."
                        print(f"  Plan  : {plan_text}")

                    if "findings" in values and values["findings"]:
                        print(f"  Findings ({len(values['findings'])}):")
                        for f in values["findings"]:
                            sev = f['severity']
                            color = RED if sev == 'CRITICAL' else YELLOW if sev == 'HIGH' else CYAN
                            print(f"    {color(f'[{sev}]')} {f['description']}")

                    # ── Messages ──
                    if "messages" in values:
                        for m in values["messages"]:
                            msg_type = m.type
                            content = m.content

                            if msg_type == "ai":
                                print(f"\n  {CYAN('[Tactician AI]')}")
                                print(f"  {content}")
                                if hasattr(m, "tool_calls") and m.tool_calls:
                                    for tc in m.tool_calls:
                                        print(f"    → Tool Call : {BOLD(tc['name'])}")
                                        print(f"      Args     : {tc['args']}")

                            elif msg_type == "tool":
                                print(f"\n  {GREEN(f'[Tool Output — {m.name}]')}")
                                print(f"  {content}")
                                # if len(content) > 500:
                                #     print(f"  {content[:500]}\n  ... [truncated, {len(content)} chars total]")
                                # else:
                                #     print(f"  {content}")

                            elif msg_type == "human":
                                if "[PLANNER" in content:
                                    print(f"\n  {MAGENTA('[Planner Directive]')}")
                                    print(f"  {content}")
                                elif "CRITICISM" in content:
                                    print(f"\n  {RED('[Critic Rejection]')}")
                                    print(f"  {content}")
                                else:
                                    print(f"\n  [Human]: {content}")

                            else:
                                print(f"\n  [{msg_type}]: {content}")

        # ── Summary ──
        print("\n" + "═" * 60)
        print(BOLD("  Execution Summary"))
        print("═" * 60)
        print(f"  Total steps   : {step}")
        print(f"  Phase history : {' → '.join(phase_history) if phase_history else 'N/A'}")
        print(GREEN("  ✓ Agent execution completed."))

    except KeyboardInterrupt:
        print(YELLOW("\n  ⚠ Interrupted by user."))
    except Exception as e:
        print(RED(f"\n  ✗ Error during execution: {e}"))
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
