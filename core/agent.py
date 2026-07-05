from django.conf import settings
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from . import rag
from .tools import AGENT_TOOLS

_checkpointer_pool = None
_graph = None


def get_chat_llm():
    if settings.LLM_PROVIDER == "ollama":
        return ChatOpenAI(model=rag.get_chat_model(), base_url=settings.OLLAMA_BASE_URL, api_key="ollama", temperature=0)
    return ChatOpenAI(model=rag.get_chat_model(), api_key=settings.OPENAI_API_KEY, temperature=0)


def _get_checkpointer_pool():
    global _checkpointer_pool
    if _checkpointer_pool is None:
        conn_string = (
            f"postgresql://{settings.DATABASES['default']['USER']}:"
            f"{settings.DATABASES['default']['PASSWORD']}@"
            f"{settings.DATABASES['default']['HOST']}:"
            f"{settings.DATABASES['default']['PORT']}/"
            f"{settings.DATABASES['default']['NAME']}"
        )
        _checkpointer_pool = ConnectionPool(
            conn_string,
            min_size=1,
            max_size=5,
            kwargs={"autocommit": True, "row_factory": dict_row},
        )
        PostgresSaver(_checkpointer_pool).setup()
    return _checkpointer_pool


def _agent_node(state):
    llm_with_tools = get_chat_llm().bind_tools(AGENT_TOOLS)
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def _should_continue(state):
    last_message = state["messages"][-1]
    return "tools" if last_message.tool_calls else END


def get_graph():
    """Build (once) and return the compiled agent graph:
    agent (decide/select tool) --[has tool_calls?]--> tools (call it) --> agent (final answer).
    """
    global _graph
    if _graph is not None:
        return _graph

    builder = StateGraph(MessagesState)
    builder.add_node("agent", _agent_node)
    builder.add_node("tools", ToolNode(AGENT_TOOLS))
    builder.set_entry_point("agent")
    builder.add_conditional_edges("agent", _should_continue, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")

    checkpointer = PostgresSaver(_get_checkpointer_pool())
    _graph = builder.compile(checkpointer=checkpointer)
    return _graph


def run_agent(thread_id, user_message):
    graph = get_graph()
    config = {"configurable": {"thread_id": str(thread_id)}}

    previous_state = graph.get_state(config)
    previous_count = len(previous_state.values.get("messages", [])) if previous_state.values else 0

    result = graph.invoke({"messages": [HumanMessage(content=user_message)]}, config=config)
    new_messages = result["messages"][previous_count:]

    tool_calls_made = [
        {"tool": m.name, "result": m.content} for m in new_messages if isinstance(m, ToolMessage)
    ]
    return {"answer": result["messages"][-1].content, "tool_calls": tool_calls_made}
