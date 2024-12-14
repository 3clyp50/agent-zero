### knowledge_tool:
- Information retrieval and analysis system.
- Combines online sources and memory systems.
- Prioritize direct solutions over guidance.
- Verify memory data against online sources.
- Provide "question" argument and get both online and memory response.
- Memory can provide guidance, online sources can provide up to date information.
- Always verify memory by online.

**Example usage**:
~~~json
{
    "thoughts": [
        "I need to gather information about...",
        "First I will search...",
        "Then I will...",
    ],
    "tool_name": "knowledge_tool",
    "tool_args": {
        "question": "How to...",
    }
}
~~~