SYNTHESIS TASK:
You are Agent Zero, synthesizing your analytical thoughts into an actionable response plan.

PROBLEM:
{original_problem}

THOUGHT PROCESS:
{thoughts}

YOUR TASK:
Transform the above thoughts into a focused execution plan that:
1. Identifies the most relevant tools for answering the question
2. Follows a logical sequence of tool usage
3. Maintains direct relevance to the user's query
4. Can be executed without further analysis

RESPONSE FORMAT:
{
    "key_insights": [
        "Main conclusions from the analysis that guide tool selection",
        "Important context that affects how tools should be used"
    ],
    "analysis": "Clear summary of how these insights inform our tool usage approach",
    "tool_sequence": [
        {
            "tool_name": "name_of_tool",
            "purpose": "What this tool will help us discover or achieve",
            "tool_args": {
                "specific": "parameters",
                "for": "this_tool"
            }
        }
    ],
    "response_plan": {
        "main_points": [
            "Key information to extract from tool results",
            "How to synthesize tool outputs into a clear answer"
        ],
        "structure": "How to present the information clearly and logically"
    }
}

REQUIREMENTS:
1. Tool sequence must directly contribute to answering the user's question
2. Each tool call must include all required parameters
3. Avoid tool calls that don't directly help answer the question
4. Keep the plan focused and efficient