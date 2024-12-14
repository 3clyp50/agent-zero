### response:
- Communication interface for task completion and status updates.
- Use for task completion notification and transition to next objective.
- Maintain continuous operation through response cycling.
- Place your result in "text" argument.

**Example usage**:
~~~json
{
    "thoughts": [
        "The user has greeted me...",
        "I will...",
    ],
    "tool_name": "response",
    "tool_args": {
        "text": "Hi...",
    }
}
~~~