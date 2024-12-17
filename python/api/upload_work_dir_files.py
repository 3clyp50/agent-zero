from python.helpers.api import ApiHandler
from flask import Request, Response, send_file

from python.helpers.file_browser import FileBrowser
from python.helpers import files
import os

class UploadWorkDirFiles(ApiHandler):

    async def process(self, input: dict, request: Request) -> dict | Response:
        if "files[]" not in request.files:
            raise Exception("No files uploaded")

        current_path = request.form.get("path", "")
        uploaded_files = request.files.getlist("files[]")

        browser = FileBrowser()

        successful, failed = browser.save_files(uploaded_files, current_path)

        if not successful and failed:
            raise Exception("All uploads failed")

        result = browser.get_files(current_path)

        return {
            "message": (
                "Files uploaded successfully"
                if not failed
                else "Some files failed to upload"
            ),
            "data": result,
            "successful": successful,
            "failed": failed,
        }

    def get_docstring(self) -> str:
        return """
        Upload Work Directory Files API
        Upload files to the working directory.
        ---
        tags:
            -   file
        parameters:
            -   in: formData
                name: files[]
                type: file
                description: List of files to be uploaded.
                required: true
            -   in: formData
                name: path
                type: string
                description: The path where the files will be uploaded.
                required: false
        responses:
            200:
                description: Files uploaded successfully.
                schema:
                    type: object
                    properties:
                        message:
                            type: string
                            description: Message indicating the result of the upload.
                        data:
                            type: array
                            items:
                                type: object
                                description: Information about the uploaded files.
                        successful:
                            type: array
                            items:
                                type: string
                            description: List of successfully uploaded files.
                        failed:
                            type: array
                            items:
                                type: string
                            description: List of files that failed to upload.
            400:
                description: No files uploaded or all uploads failed.
                schema:
                    type: object
                    properties:
                        error:
                            type: string
                            description: Error message indicating the issue.
        """

    def get_supported_http_method(self) -> str:
        return "POST"
