import re


def create_background_command(command: str) -> str:
    """
    Wraps a command with nohup, adding > /dev/null 2>&1 only if no redirection exists.
    Ensures it runs in the background and appends echo $! to capture the PID.
    """
    # Check if the command contains any output redirection
    if not re.search(r"(\>|\>>|2>&1)", command):
        # No redirection found, add > /dev/null 2>&1
        command = f"{command} > /dev/null 2>&1"

    # Wrap with nohup, add & echo $!
    bg_command = f"nohup {command} & echo $!\n"
    return bg_command
