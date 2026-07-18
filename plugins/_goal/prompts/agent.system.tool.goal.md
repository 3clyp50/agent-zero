### goal
Inspect, create, or finish the current chat goal.

Use this only when the user asks for a goal or asks you to manage one. Do not create goals for casual replies or ordinary one-shot answers.

Actions:
- `get`: inspect the current goal; use this before creating one when its state is unknown.
- `create`: make the given concise `objective` active; optional positive `token_budget`.
- `update`: mark the current goal with `status` `complete` or `blocked`; optional revised `objective` and `note`.

Pause, resume, edit, and delete are user controls. Mark `complete` only after achieving the objective; mark `blocked` only after viable alternatives are exhausted and work cannot continue without user input or an external-state change.

Example:
~~~json
{
  "thoughts": ["The user asked me to manage this task as a goal."],
  "headline": "Creating goal",
  "tool_name": "goal",
  "tool_args": {
    "action": "create",
    "objective": "Add the built-in goal plugin with a Web UI strip and slash command"
  }
}
~~~
