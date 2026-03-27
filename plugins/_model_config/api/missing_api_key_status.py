from helpers.api import ApiHandler, Request, Response
from plugins._model_config.helpers import model_config


class MissingApiKeyStatus(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        missing_providers = model_config.get_missing_api_key_providers()
        return {
            "missing_providers": missing_providers,
            "has_missing_api_keys": bool(missing_providers),
        }
