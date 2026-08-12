from helpers.history import output_langchain
from langchain_core.messages import AIMessage, HumanMessage


def test_output_langchain_omits_leading_assistant_messages():
    messages = output_langchain(
        [
            {"ai": True, "content": "Welcome"},
            {"ai": False, "content": "Hello"},
            {"ai": True, "content": "Hi"},
        ]
    )

    assert messages == [HumanMessage("Hello"), AIMessage("Hi")]
