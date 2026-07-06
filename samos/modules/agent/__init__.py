from samos.modules.agent.tools import (
    agent_briefing_tool,
    agent_context_tool,
    agent_query_tool,
    agent_remember_tool,
    agent_search_tool,
)

MODULE = {
    "name": "agent",
    "display_name": "Agent Interface",
    "description": "Unified views and memory for upstream agents.",
    "tools": [
        agent_context_tool,
        agent_query_tool,
        agent_search_tool,
        agent_briefing_tool,
        agent_remember_tool,
    ],
    "resources": [],
    "scheduler_jobs": [],
}
