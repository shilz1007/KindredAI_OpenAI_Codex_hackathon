"""Internal Router Agent: model-led intent selection with no MCP permissions."""

from kindred_ai.application.ports.agent_router import AgentRoute, AgentRouter
from kindred_ai.infrastructure.observability import observation, record_output


class RouterAgent:
    """Owns route selection; it cannot converse with users or execute actions."""

    def __init__(self, router_model: AgentRouter) -> None:
        self._router_model = router_model

    def route(self, message: str) -> AgentRoute:
        """Return one validated route for Master to execute."""
        with observation(
            "agent.router",
            as_type="agent",
            input={"message": message},
            metadata={"agent": "router", "mcp_access": "none"},
        ) as trace:
            route = self._router_model.route(message)
            record_output(trace, route.model_dump())
            return route
