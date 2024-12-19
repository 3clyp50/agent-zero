import asyncio
from dataclasses import dataclass
import shlex
import time
from python.helpers.tool import Tool, Response
from python.helpers import files, rfc_exchange
from python.helpers.print_style import PrintStyle
from python.helpers.shell_local import LocalInteractiveSession
from python.helpers.shell_ssh import SSHInteractiveSession
from python.helpers.docker import DockerContainerManager

@dataclass
class State:
    shell: LocalInteractiveSession | SSHInteractiveSession
    docker: DockerContainerManager | None

class CodeExecution(Tool):

    async def execute(self, **kwargs):
        await self.agent.handle_intervention()  # wait for intervention and handle it, if paused
        await self._prepare_state()

        runtime = self.args.get("runtime", "").lower().strip()

        if runtime == "python":
            response = await self._execute_python_code(self.args["code"])
        elif runtime == "nodejs":
            response = await self._execute_nodejs_code(self.args["code"])
        elif runtime == "terminal":
            response = await self._execute_terminal_command(self.args["code"])
        elif runtime == "output":
            response = await self._get_terminal_output(
                wait_with_output=5, wait_without_output=60
            )
        elif runtime == "reset":
            response = await self._reset_terminal()
        elif runtime == "background":
            response = await self._start_background_process(self.args["command"])
        else:
            response = self.agent.read_prompt(
                "fw.code_runtime_wrong.md", runtime=runtime
            )

        if not response:
            response = self.agent.read_prompt("fw.code_no_output.md")
        return Response(message=response, break_loop=False)

    def get_log_object(self):
        return self.agent.context.log.log(type="code_exe", heading=f"{self.agent.agent_name}: Using tool '{self.name}'", content="", kvps=self.args)

    async def after_execution(self, response, **kwargs):
        await self.agent.hist_add_tool_result(self.name, response.message)

    async def _prepare_state(self, reset=False):
        self.state = self.agent.get_data("_cot_state")
        if not self.state or reset:
            # initialize docker container if execution in docker is configured
            if self.agent.config.code_exec_docker_enabled:
                docker = DockerContainerManager(
                    logger=self.agent.context.log,
                    name=self.agent.config.code_exec_docker_name,
                    image=self.agent.config.code_exec_docker_image,
                    ports=self.agent.config.code_exec_docker_ports,
                    volumes=self.agent.config.code_exec_docker_volumes,
                )
                docker.start_container()
            else:
                docker = None

            # initialize local or remote interactive shell interface
            # if self.agent.config.code_exec_ssh_enabled:
            #     shell = await self._setup_ssh_shell()
            # else:
            shell = await self._setup_local_shell()

            self.state = State(shell=shell, docker=docker)
            await shell.connect()
        self.agent.set_data("_cot_state", self.state)

    async def _setup_ssh_shell(self):
        pswd = self.agent.config.code_exec_ssh_pass if self.agent.config.code_exec_ssh_pass else await rfc_exchange.get_root_password()
        return SSHInteractiveSession(
            self.agent.context.log,
            self.agent.config.code_exec_ssh_addr,
            self.agent.config.code_exec_ssh_port,
            self.agent.config.code_exec_ssh_user,
            pswd,
        )

    async def _setup_local_shell(self):
        return LocalInteractiveSession()

    async def _execute_python_code(self, code: str, reset: bool = False):
        escaped_code = shlex.quote(code)
        command = f"ipython -c {escaped_code}"
        return await self._terminal_session(command, reset)

    async def _execute_nodejs_code(self, code: str, reset: bool = False):
        escaped_code = shlex.quote(code)
        command = f"node /exe/node_eval.js {escaped_code}"
        return await self._terminal_session(command, reset)

    async def _execute_terminal_command(self, command: str, reset: bool = False):
        return await self._terminal_session(command, reset)

    async def _terminal_session(self, command: str, reset: bool = False):
        await self.agent.handle_intervention()  # wait for intervention and handle it, if paused
        # try again on lost connection
        for i in range(2):
            try:
                if reset:
                    await self._reset_terminal()

                self.state.shell.send_command(command)

                PrintStyle(background_color="white", font_color="#1B4F72", bold=True).print(
                    f"{self.agent.agent_name} code execution output"
                )
                return await self._get_terminal_output()

            except Exception as e:
                if i == 1:
                    # try again on lost connection
                    PrintStyle.error(str(e))
                    await self._prepare_state(reset=True)
                    continue
                else:
                    raise e

    async def _get_terminal_output(
        self,
        reset_full_output=True,
        wait_with_output=3,
        wait_without_output=10,
        max_exec_time=60,
    ):
        idle = 0
        SLEEP_TIME = 0.1
        start_time = time.time()
        full_output = ""

        while max_exec_time <= 0 or time.time() - start_time < max_exec_time:
            await asyncio.sleep(SLEEP_TIME)  # Wait for some output to be generated
            full_output, partial_output = await self.state.shell.read_output(
                timeout=max_exec_time, reset_full_output=reset_full_output
            )
            reset_full_output = False # only reset once

            await self.agent.handle_intervention()  # wait for intervention and handle it, if paused

            if partial_output:
                PrintStyle(font_color="#85C1E9").stream(partial_output)
                self.log.update(content=full_output)
                idle = 0
            else:
                idle += 1
                if (full_output and idle > wait_with_output / SLEEP_TIME) or (
                    not full_output and idle > wait_without_output / SLEEP_TIME
                ):
                    break
        return full_output

    async def _reset_terminal(self):
        self.state.shell.close()
        await self._prepare_state(reset=True)
        response = self.agent.read_prompt("fw.code_reset.md")
        self.log.update(content=response)
        return response

    async def _start_background_process(self, command: str) -> str:
        """
        Start a background process and return its PID.
        """
        local_shell = await self._setup_local_shell()
        await local_shell.connect()

        pid = await local_shell.start_background_command(command)
        if pid:
            response = f"Process started in background with PID: {pid}"
        else:
            response = "Failed to start the background process."
        return response
