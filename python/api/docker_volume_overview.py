from python.helpers.api import ApiHandler, Request, Response
from python.helpers.docker import get_agent_zero_volume_snapshot


class DockerVolumeOverview(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return True

    @classmethod
    def requires_loopback(cls) -> bool:
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        snapshot = get_agent_zero_volume_snapshot()
        return snapshot
