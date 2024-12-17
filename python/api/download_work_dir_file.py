from python.helpers.api import ApiHandler
from flask import Request, Response, send_file
from python.helpers.file_browser import FileBrowser
from python.helpers import files
import os

class DownloadWorkDirFile(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        file_path = request.args.get("path", "")
        if not file_path:
            raise ValueError("No file path provided")

        browser = FileBrowser()

        full_path = browser.get_full_path(file_path, True)
        if os.path.isdir(full_path):
            zip_file = browser.zip_dir(full_path)
            return send_file(
                zip_file,
                as_attachment=True,
                download_name=f"{os.path.basename(file_path)}.zip",
            )
        if full_path:
            return send_file(
                full_path, as_attachment=True, download_name=os.path.basename(file_path)
            )
        raise Exception("File not found")

    def get_docstring(self) -> str:
        return """
        Download Work Directory File API
        Download a file or directory from the work directory.
        ---
        tags:
            -   file
        parameters:
            -   in: query
                name: path
                required: true
                description: The path to the file or directory to download.
                schema:
                    type: string
        responses:
            200:
                description: File or directory downloaded successfully.
                schema:
                    type: file
            400:
                description: No file path provided.
                schema:
                    type: object
                    properties:
                        error:
                            type: string
                            description: Error message indicating no file path was provided.
            404:
                description: File not found.
                schema:
                    type: object
                    properties:
                        error:
                            type: string
                            description: Error message indicating the file was not found.
        """

    def get_supported_http_method(self) -> str:
        return "GET"
