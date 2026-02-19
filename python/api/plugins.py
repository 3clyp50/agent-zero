from python.helpers.api import ApiHandler, Request, Response
from python.helpers import plugins


class Plugins(ApiHandler):
    """
    Core plugin management API.
    Actions: list, get_settings, save_settings
    """

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "list")

        if action == "list":
            tab = input.get("tab")  # optional: filter by settings_tab
            data = plugins.list_plugins_with_metadata(tab_filter=tab or None)
            return {"ok": True, "data": data}

        if action == "get_settings":
            plugin_name = input.get("plugin_name", "")
            project_name = input.get("project_name", "")
            agent_profile = input.get("agent_profile", "")
            if not plugin_name:
                return Response(status=400, response="Missing plugin_name")
            settings = plugins.get_plugin_settings(plugin_name,
                                                   project_name=project_name,
                                                   agent_profile=agent_profile)
            return {"ok": True, "data": settings or {}}

        if action == "save_settings":
            plugin_name = input.get("plugin_name", "")
            project_name = input.get("project_name", "")
            agent_profile = input.get("agent_profile", "")
            settings = input.get("settings", {})
            if not plugin_name:
                return Response(status=400, response="Missing plugin_name")
            plugins.save_plugin_settings(plugin_name, project_name, agent_profile, settings)
            return {"ok": True}

        return Response(status=400, response=f"Unknown action: {action}")
