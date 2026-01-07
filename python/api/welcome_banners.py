from python.helpers.api import ApiHandler, Request, Response


class WelcomeBanners(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        # Placeholder for backend-generated welcome banners.
        # Frontend provides context and any precomputed banners.
        _ = input.get("frontend_banners", [])
        _ = input.get("context", {})
        return {"banners": []}
