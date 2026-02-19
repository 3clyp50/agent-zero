from __future__ import annotations

import re, json
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from python.helpers import files, print_style
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from agent import Agent

# Extracts target selector from <meta name="plugin-target" content="...">
_META_TARGET_RE = re.compile(
    r'<meta\s+name=["\']plugin-target["\']\s+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)

META_FILE_NAME = "plugin.json"
CONFIG_FILE_NAME = "config.json"
DISABLED_FILE_NAME = ".disabled"
ENABLED_FILE_NAME = ".enabled"


class PluginMetadata(BaseModel):
    name: str = ""
    description: str = ""
    version: str = ""
    settings_sections: List[str] = Field(default_factory=list)
    per_project_config: bool = False
    per_agent_config: bool = False


class PluginListItem(BaseModel):
    name: str
    path: str
    display_name: str = ""
    description: str = ""
    version: str = ""
    settings_sections: List[str] = Field(default_factory=list)
    per_project_config: bool = False
    per_agent_config: bool = False
    is_custom: bool = False
    has_main_screen: bool = False
    has_config_screen: bool = False


def get_plugin_roots() -> List[str]:
    """Plugin root directories, ordered by priority (user first)."""
    return [
        files.get_abs_path(files.USER_DIR, files.PLUGINS_DIR),
        files.get_abs_path(files.PLUGINS_DIR),
    ]


def get_plugins_list():
    result: list[str] = []
    seen_names: set[str] = set()
    for root in get_plugin_roots():
        for dir in Path(root).iterdir():
            if not dir.is_dir() or dir.name.startswith("."):
                continue
            if dir.name in seen_names:
                continue
            if files.exists(str(dir), META_FILE_NAME):
                seen_names.add(dir.name)
                result.append(dir.name)
    result.sort(key=lambda p: Path(p).name)
    return result


def get_enhanced_plugins_list(
    custom: bool = True, builtin: bool = True
) -> List[PluginListItem]:
    """Discover plugins by directory convention. First root wins on ID conflict."""
    results = []

    def load_plugins(root_path: str, is_custom: bool):
        for d in sorted(Path(root_path).iterdir(), key=lambda p: p.name):
            try:
                if not d.is_dir() or d.name.startswith("."):
                    continue
                meta = PluginMetadata.model_validate(
                    files.read_file_json(str(d / META_FILE_NAME))
                )
                has_main_screen = files.exists(str(d / "webui" / "main.html"))
                has_config_screen = files.exists(str(d / "webui" / "config.html"))
                results.append(
                    PluginListItem(
                        name=d.name,
                        path=str(d),
                        display_name=meta.name or d.name,
                        description=meta.description,
                        version=meta.version,
                        settings_sections=meta.settings_sections,
                        per_project_config=meta.per_project_config,
                        per_agent_config=meta.per_agent_config,
                        is_custom=is_custom,
                        has_main_screen=has_main_screen,
                        has_config_screen=has_config_screen,
                    )
                )
            except:
                pass

    if custom:
        load_plugins(files.get_abs_path(files.USER_DIR, files.PLUGINS_DIR), True)
    if builtin:
        load_plugins(files.get_abs_path(files.PLUGINS_DIR), False)
    return results


def find_plugin_dir(plugin_name: str):
    if not plugin_name:
        return None

    # check if the plugin is in the user directory
    user_plugin_path = files.get_abs_path(
        files.USER_DIR, files.PLUGINS_DIR, plugin_name, META_FILE_NAME
    )
    if files.exists(user_plugin_path):
        return files.get_abs_path(files.USER_DIR, files.PLUGINS_DIR, plugin_name)

    # check if the plugin is in the default directory
    default_plugin_path = files.get_abs_path(
        files.PLUGINS_DIR, plugin_name, META_FILE_NAME
    )
    if files.exists(default_plugin_path):
        return files.get_abs_path(files.PLUGINS_DIR, plugin_name)

    return None


def get_plugin_paths(*subpaths: str) -> List[str]:
    sub = "*/" + "/".join(subpaths) if subpaths else "*"
    paths: List[str] = []
    for root in get_plugin_roots():
        paths.extend(
            files.find_existing_paths_by_pattern(files.get_abs_path(root, sub))
        )
    return paths

def get_enabled_plugin_paths(agent:Agent|None, *subpaths: str) -> List[str]:
    enabled = get_enabled_plugins(agent)
    paths: list[str] = []

    for plugin in enabled:
        base_dir = find_plugin_dir(plugin)
        if not base_dir:
            continue

        if not subpaths:
            if files.exists(base_dir):
                paths.append(base_dir)
            continue

        path = files.get_abs_path(base_dir, *subpaths)
        if files.exists(path):
            paths.append(path)

    return paths


def get_enabled_plugins(agent: Agent | None):
    plugins = get_plugins_list()
    active = []

    if agent:
        from python.helpers import subagents
        
    for plugin in plugins:
        # plugins are toggled via .enabled / .disabled files
        # every plugin is on by default, unless disabled in usr dir
        enabled = True

        if agent:
            agent_paths = subagents.get_paths(
                    agent,
                    files.PLUGINS_DIR,
                    plugin,
                    must_exist_completely=True,
                    include_default=False,
                    include_user=True,
                    include_plugins=False,
                    include_project=True
                )

            # go through agent paths in reverse order and determine the state
            for agent_path in reversed(agent_paths):
                if enabled:
                    enabled = not files.exists(files.get_abs_path(agent_path, DISABLED_FILE_NAME))
                else:
                    enabled = files.exists(files.get_abs_path(agent_path, ENABLED_FILE_NAME))


        if enabled:
            active.append(plugin)
    
    return active



def get_webui_extensions(extension_point: str, filters: List[str] | None = None):
    entries: List[str] = []
    effective_filters = filters or ["*"]

    for filter in effective_filters:
        extensions = get_plugin_paths("extensions", "webui", extension_point, filter)
        for extension in extensions:
            rel_path = files.deabsolute_path(extension)
            entries.append(rel_path)

    return entries


def get_plugin_config(plugin_name: str, agent: Agent | None):
    file_path = find_plugin_asset(plugin_name, CONFIG_FILE_NAME, agent=agent)
    if file_path:
        return json.loads(files.read_file(file_path))
    return None


def save_plugin_config(
    plugin_name: str, project_name: str, agent_profile: str, settings: dict
):
    file_path = determine_plugin_asset_path(
        plugin_name, project_name, agent_profile, CONFIG_FILE_NAME
    )
    if file_path:
        files.write_file(file_path, json.dumps(settings))


def find_plugin_asset(plugin_name: str, *subpaths: str, agent: Agent | None = None):
    project_name = ""

    if agent:
        profile_name = agent.config.profile if agent and agent.config.profile else ""

        from python.helpers import projects

        project_name = projects.get_context_project_name(agent.context) or ""

        if project_name and profile_name:
            # project/.a0proj/agents/<profile>/plugins/<plugin_name>/...
            project_agent_file = projects.get_project_meta(
                project_name,
                files.AGENTS_DIR,
                profile_name,
                files.PLUGINS_DIR,
                plugin_name,
                *subpaths,
            )
            if files.exists(project_agent_file):
                return project_agent_file

        if project_name:
            # project/.a0proj/plugins/<plugin_name>/...
            project_file = projects.get_project_meta(
                project_name, files.PLUGINS_DIR, plugin_name, *subpaths
            )
            if files.exists(project_file):
                return project_file

        if profile_name:
            from python.helpers import subagents

            # usr/agents/<profile>/plugins/<plugin_name>/...
            path = files.get_abs_path(
                subagents.USER_AGENTS_DIR,
                profile_name,
                files.PLUGINS_DIR,
                plugin_name,
                *subpaths,
            )
            if files.exists(path):
                return path

            # agents/<profile>/plugins/<plugin_name>/...
            path = files.get_abs_path(
                subagents.DEFAULT_AGENTS_DIR,
                profile_name,
                files.PLUGINS_DIR,
                plugin_name,
                *subpaths,
            )
            if files.exists(path):
                return path

    # usr/plugins/<plugin_name>/...
    path = files.get_abs_path(files.USER_DIR, files.PLUGINS_DIR, plugin_name, *subpaths)
    if files.exists(path):
        return path

    # plugins/<plugin_name>/...
    path = files.get_abs_path(files.PLUGINS_DIR, plugin_name, *subpaths)
    if files.exists(path):
        return path

    return None


def determine_plugin_asset_path(
    plugin_name: str, project_name: str, agent_profile: str, *subpaths: str
):
    base_path = files.get_abs_path(files.USER_DIR)

    if project_name:
        from python.helpers import projects

        base_path = projects.get_project_meta(project_name)

    if agent_profile:
        base_path = files.get_abs_path(base_path, files.AGENTS_DIR, agent_profile)

    return files.get_abs_path(base_path, files.PLUGINS_DIR, plugin_name, *subpaths)
