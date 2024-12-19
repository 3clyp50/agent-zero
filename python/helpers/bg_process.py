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

    # Check if the command already contains nohup
    if not re.search(r"\bnohup\b", command):
        # Add nohup if not present
        command = f"nohup {command}"

    # Check if the command already ends with &
    if not re.search(r"&\s*$", command):
        # Add & if not present
        command = f"{command} &"

    # Append echo $! to capture the PID
    bg_command = f"{command} echo $!\n"
    return bg_command