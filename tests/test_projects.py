from pathlib import Path

from helpers import dirty_json, files, projects


def _prepare_project_tree(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(files, "_base_dir", str(tmp_path))
    (tmp_path / "usr" / "projects").mkdir(parents=True, exist_ok=True)
    (tmp_path / "usr" / "plugins").mkdir(parents=True, exist_ok=True)
    (tmp_path / "plugins").mkdir(parents=True, exist_ok=True)


def test_project_include_agents_md_defaults_true_and_saves(monkeypatch, tmp_path):
    _prepare_project_tree(monkeypatch, tmp_path)
    meta = tmp_path / "usr" / "projects" / "demo" / ".a0proj"
    meta.mkdir(parents=True)
    (meta / "project.json").write_text('{"title": "Demo"}', encoding="utf-8")

    data = projects.load_basic_project_data("demo")

    assert data["include_agents_md"] is True

    projects.save_project_header("demo", data)
    saved = dirty_json.parse((meta / "project.json").read_text(encoding="utf-8"))

    assert saved["include_agents_md"] is True


def test_project_mcp_servers_persist_in_project_meta(monkeypatch, tmp_path):
    _prepare_project_tree(monkeypatch, tmp_path)
    config = '{"mcpServers":{"demo":{"url":"https://example.com/mcp"}}}'

    projects.create_project(
        "demo",
        {
            "title": "Demo",
            "mcp_servers": config,
        },
    )

    assert projects.load_project_mcp_servers("demo") == config
    assert projects.load_edit_project_data("demo")["mcp_servers"] == config

    updated = '{"mcpServers":{"other":{"command":"uvx","args":["pkg"]}}}'
    projects.save_project_mcp_servers("demo", updated)

    assert projects.load_project_mcp_servers("demo") == updated


def test_project_mcp_servers_reject_path_names(monkeypatch, tmp_path):
    _prepare_project_tree(monkeypatch, tmp_path)

    for name in ("../escape", "nested/project", ".", "..", ""):
        try:
            projects.save_project_mcp_servers(name, '{"mcpServers":{}}')
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected invalid project name: {name!r}")


def test_project_system_prompt_includes_root_agents_md_with_path(monkeypatch, tmp_path):
    _prepare_project_tree(monkeypatch, tmp_path)
    projects.create_project(
        "demo",
        {
            "title": "Demo",
            "instructions": "Main project rule.",
        },
    )
    project_root = tmp_path / "usr" / "projects" / "demo"
    (project_root / "AGENTS.md").write_text("Root AGENTS rule.", encoding="utf-8")
    (
        project_root / ".a0proj" / "instructions" / "extra.md"
    ).write_text("Folder instruction rule.", encoding="utf-8")

    prompt_vars = projects.build_system_prompt_vars("demo")
    instructions = prompt_vars["project_instructions"]

    assert "Main project rule." in instructions
    assert instructions.count("## project instruction files") == 1
    assert "## project instruction file\n" not in instructions
    assert "### path: /a0/usr/projects/demo/AGENTS.md" in instructions
    assert "Root AGENTS rule." in instructions
    assert "### path: /a0/usr/projects/demo/.a0proj/instructions/extra.md" in instructions
    assert "Folder instruction rule." in instructions


def test_project_system_prompt_respects_disabled_agents_md(monkeypatch, tmp_path):
    _prepare_project_tree(monkeypatch, tmp_path)
    projects.create_project(
        "demo",
        {
            "title": "Demo",
            "include_agents_md": False,
        },
    )
    project_root = tmp_path / "usr" / "projects" / "demo"
    (project_root / "AGENTS.md").write_text("Root AGENTS rule.", encoding="utf-8")

    prompt_vars = projects.build_system_prompt_vars("demo")

    assert "Root AGENTS rule." not in prompt_vars["project_instructions"]
    assert "AGENTS.md" not in prompt_vars["project_instructions"]
