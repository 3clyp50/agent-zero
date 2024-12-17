from python.helpers.api import ApiHandler
from flask import Request, Response

from python.helpers.file_browser import FileBrowser
from python.helpers import files

class DeleteWorkDirFile(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        file_path = input.get('path', '')
        current_path = input.get('currentPath', '')

        browser = FileBrowser()

        if browser.delete_file(file_path):
            # Get updated file list
            result = browser.get_files(current_path)
            return {
                "data": result
            }
        else:
            raise Exception("File not found or could not be deleted")

    def get_docstring(self) -> str:
        return """
        Delete Work Directory File API
        Delete a file from the work directory.
        ---
        tags:
            -   file
        parameters:
            -   in: body
                name: body
                required: true
                schema:
                    id: DeleteWorkDirFileRequest
                    required:
                        - path
                        - currentPath
                    properties:
                        path:
                            type: string
                            description: The path of the file to be deleted.
                        currentPath:
                            type: string
                            description: The current directory path.
        responses:
            200:
                description: File deleted successfully.
                schema:
                    type: object
                    properties:
                        data:
                            type: array
                            description: Updated list of files in the current directory.
            404:
                description: File not found or could not be deleted.
                schema:
                    type: object
                    properties:
                        error:
                            type: string
                            description: Error message indicating the file was not found or could not be deleted.
        """

    def get_supported_http_method(self) -> str:
        return "POST"
