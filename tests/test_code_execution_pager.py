"""Regression tests for code execution shell lifecycle behavior.

Pagers (more/less) must be disabled in the non-interactive shells created by the
code execution tool: without user input they block forever and spin at 100% CPU.
"""

import asyncio

from plugins._code_execution.helpers import shell_local, shell_ssh
from plugins._code_execution.helpers.tty_session import TTYSession


def test_local_env_disables_pagers_and_preserves_existing():
    env = shell_local.disable_pagers_in_env({"PATH": "/usr/bin", "PAGER": "less"})
    assert env["PAGER"] == "cat"
    assert env["GIT_PAGER"] == "cat"
    # pre-existing keys are preserved
    assert env["PATH"] == "/usr/bin"


def test_local_env_defaults_to_environ():
    env = shell_local.disable_pagers_in_env()
    assert env["PAGER"] == "cat"
    assert env["GIT_PAGER"] == "cat"


def test_local_env_does_not_mutate_input():
    src = {"PATH": "/usr/bin"}
    shell_local.disable_pagers_in_env(src)
    assert src == {"PATH": "/usr/bin"}


def test_ssh_command_disables_pagers():
    assert "GIT_PAGER=cat" in shell_ssh.PAGER_DISABLE_COMMAND
    assert "PAGER=cat" in shell_ssh.PAGER_DISABLE_COMMAND


def test_tty_close_kills_term_resistant_process():
    async def run():
        session = TTYSession("bash -lc 'trap \"\" TERM; sleep 30'")
        await session.start()
        await asyncio.wait_for(session.close(), timeout=6)
        assert session._proc is None

    asyncio.run(run())
