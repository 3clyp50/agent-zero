### behaviour_adjustment:
Modify operational parameters based on runtime requirements.
Updates core behavioral protocols through "adjustments" argument.
Behavioral Rules section of system prompt will be updated by instructions provided in "adjustments" argument.
**Example usage**:
~~~json
{
    "thoughts": [
        "Analyzing behavioral modification requirements...",
        "Implementing adjusted Python-expert behavior...",
    ],
    "tool_name": "behaviour_update",
    "tool_args": {
        "adjustments": "Stop formatting with 4 tabs... Always do...",
    }
}
~~~