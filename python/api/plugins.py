from python.helpers.api import ApiHandler, Request, Response
from python.helpers import plugins, files


class Plugins(ApiHandler):
    """
    Core plugin management API.
    Actions: get_config, save_config
    """

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "get_config")

        # Accept legacy aliases during migration.
        if action in {"get_config", "get_settings"}:
            plugin_name = input.get("plugin_name", "")
            project_name = input.get("project_name", "")
            agent_profile = input.get("agent_profile", "")
            if not plugin_name:
                return Response(status=400, response="Missing plugin_name")

            settings = None
            if project_name or agent_profile:
                file_path = plugins.determine_plugin_asset_path(
                    plugin_name,
                    project_name,
                    agent_profile,
                    plugins.CONFIG_FILE_NAME,
                )
                if files.exists(file_path):
                    settings = files.read_file_json(file_path)

            if settings is None:
                settings = plugins.get_plugin_config(plugin_name, agent=None)

            return {"ok": True, "data": settings or {}}

        if action in {"save_config", "save_settings"}:
            plugin_name = input.get("plugin_name", "")
            project_name = input.get("project_name", "")
            agent_profile = input.get("agent_profile", "")
            settings = input.get("settings", {})
            if not plugin_name:
                return Response(status=400, response="Missing plugin_name")
            if not isinstance(settings, dict):
                return Response(status=400, response="settings must be an object")
            plugins.save_plugin_config(plugin_name, project_name, agent_profile, settings)
            return {"ok": True}

        return Response(status=400, response=f"Unknown action: {action}")
