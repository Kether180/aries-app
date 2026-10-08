class UpstreamError(Exception):
    """A third-party API (news or OpenAI) failed. Mapped to 502 in main.py."""

    def __init__(self, service: str, message: str, status_code: int = 502):
        super().__init__(f"{service}: {message}")
        self.service = service
        self.message = message
        self.status_code = status_code
