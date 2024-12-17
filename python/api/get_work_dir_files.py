from python.helpers.api import ApiHandler
from flask import Request, Response

from python.helpers.file_browser import FileBrowser
from python.helpers import files, runtime

class GetWorkDirFiles(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        current_path = request.args.get("path", "")
        if current_path == "$WORK_DIR":
            if runtime.is_development():
                current_path = "work_dir"
            else:
                current_path = "root"
        browser = FileBrowser()
        result = browser.get_files(current_path)

        return {"data": result}

    def get_docstring(self) -> str:
        return """
        GetWorkDirFiles API Request
        Retrieve the list of files in the specified directory.
        ---
        tags:
            - file
        parameters:
            - in: query
              name: path
              required: true
              type: string
              description: The path to the directory. Use "$WORK_DIR" to refer to the working directory.
        responses:
            200:
                description: A list of files in the specified directory.
                schema:
                    type: object
                    properties:
                        data:
                            type: array
                            items:
                                type: string
                            description: List of file names in the specified directory.
            400:
                description: Bad request, invalid path.
                schema:
                    type: object
                    properties:
                        error:
                            type: string
                            description: Error message indicating the issue.
        """

    def get_supported_http_method(self) -> str:
        return "GET"
