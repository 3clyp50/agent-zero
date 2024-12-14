### call_subordinate:
Coordinate with specialized agent instances for task execution.
- "message": Define role and task specifications
- "reset": true for new instance, false for continued interaction
- Provide comprehensive context and specific directives

**Example usage**:
~~~json
{
    "thoughts": [
        "The result seems to be ok but...",
        "I will ask my subordinate to fix...",
    ],
    "tool_name": "call_subordinate",
    "tool_args": {
        "message": "Well done, now edit...",
        "reset": "false"
    }
}
~~~