class AppError(Exception):
    """Domain error mapped to an HTTP response by the API layer."""

    def __init__(self, status_code: int, detail: str, code: str | None = None) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(detail)


class BadRequestError(AppError):
    def __init__(self, detail: str, code: str | None = None) -> None:
        super().__init__(400, detail, code)


class ForbiddenError(AppError):
    def __init__(self, detail: str, code: str | None = None) -> None:
        super().__init__(403, detail, code)


class NotFoundError(AppError):
    def __init__(self, detail: str, code: str | None = None) -> None:
        super().__init__(404, detail, code)


class ConflictError(AppError):
    def __init__(self, detail: str, code: str | None = None) -> None:
        super().__init__(409, detail, code)
