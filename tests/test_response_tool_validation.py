import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from helpers.errors import RepairableException
from tools.response import ResponseTool


@pytest.mark.asyncio
@pytest.mark.parametrize("args", [{"text": "ok"}, {"message": "ok"}])
async def test_response_tool_accepts_text_or_message(args) -> None:
    tool = ResponseTool(None, "response", None, args, "", None)

    response = await tool.execute()

    assert response.message == "ok"
    assert response.break_loop is True


@pytest.mark.asyncio
async def test_response_tool_rejects_nested_response_args() -> None:
    tool = ResponseTool(
        None,
        "response",
        None,
        {
            "thoughts": [],
            "headline": "Providing exact payload",
            "tool_name": "response",
            "tool_args": {"text": "nested"},
        },
        "",
        None,
    )

    with pytest.raises(RepairableException, match="top-level text or message"):
        await tool.execute()
