### code_execution_tool:
Execute provided terminal commands, Python code, Node.js code, or start background processes. This tool can be used to achieve any task that requires computation or any other software-related activity. Place your code escaped and properly indented in the "code" argument. Select the corresponding runtime with the "runtime" argument. Possible values are "terminal", "python", and "nodejs" for code, "output" and "reset" for additional actions, and "background" for starting background processes.

Sometimes a dialogue can occur in the output, such as questions like Y/N. In that case, use the "terminal" runtime in the next step and send your answer. If the code is running long, you can use the runtime "output" to wait for the next output part or use the runtime "reset" to kill the process. You can use pip, npm, and apt-get in the terminal runtime to install any required packages.

IMPORTANT: Never use implicit print or implicit output; it does not work! If you need the output of your code, you MUST use print() or console.log() to output selected variables. When the tool outputs an error, you need to change your code accordingly before trying again. The knowledge_tool can help analyze errors.

IMPORTANT!: Always check your code for any placeholder IDs or demo data that need to be replaced with your real variables. Do not simply reuse code snippets from tutorials.

IMPORTANT: Use the "background" runtime over the "terminal" runtime for long-running and non-blocking processes like GUI applications.

Do not use in combination with other tools except for thoughts. Wait for the response before using other tools.

**Example usages:**
1. Execute python code
~~~json
{
    "thoughts": [
        "I need to do...",
        "I can use library...",
        "Then I can...",
    ],
    "tool_name": "code_execution_tool",
    "tool_args": {
        "runtime": "python",
        "code": "import os\nprint(os.getcwd())",
    }
}
~~~

2. Execute terminal command
~~~json
{
    "thoughts": [
        "I need to do...",
        "I need to install...",
    ],
    "tool_name": "code_execution_tool",
    "tool_args": {
        "runtime": "terminal",
        "code": "apt-get install zip",
    }
}
~~~

2. 1. Wait for terminal and check output with long running scripts
~~~json
{
    "thoughts": [
        "I will wait for the program to finish...",
    ],
    "tool_name": "code_execution_tool",
    "tool_args": {
        "runtime": "output",
    }
}
~~~

2. 2. Reset terminal
~~~json
{
    "thoughts": [
        "Code execution tool is not responding...",
    ],
    "tool_name": "code_execution_tool",
    "tool_args": {
        "runtime": "reset",
    }
}
~~~

3. Start a background process
~~~json
{
    "thoughts": [
        "I need to start a non-blocking background process...",
        "This process should run independently...",
    ],
    "tool_name": "code_execution_tool",
    "tool_args": {
        "runtime": "background",
        "command": "python3 -m http.server 8080",
    }
}
~~~

3. 1. Start a background process and log its output to a file for later analysis.
~~~json
{
    "thoughts": [
        "I need to start a non-blocking background process...",
        "I should log the output to analyze it afterwards...",
        "This process should run independently...",
    ],
    "tool_name": "code_execution_tool",
    "tool_args": {
        "runtime": "background",
        "command": "long_running_script.sh > output.log 2>&1",
    }
}
~~~