from python.helpers.api import ApiHandler, Request, Response
from python.helpers.persistent_storage import sync_persistent_content


class PersistentSync(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return True

    @classmethod
    def requires_loopback(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request) -> dict | Response:
        direction = (input.get("direction") or "").lower()
        target_path = (input.get("target_path") or "").strip()
        items = input.get("items", []) or []
        clean_destination = bool(input.get("clean_destination", False))

        if not target_path:
            return {"success": False, "error": "Target path is required."}

        result = sync_persistent_content(
            direction=direction,
            target_path=target_path,
            items=items,
            clean_destination=clean_destination,
        )
        return result
