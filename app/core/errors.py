"""Domain errors shared by every service.

Services raise these; `app/main.py` maps each base class to an HTTP status code,
so routes do not need their own try/except blocks.
"""


class BadRequestError(Exception):
    """The request is well-formed but cannot be acted on (400)."""


class ForbiddenError(Exception):
    """The caller is not allowed to perform this action (403)."""


class NotFoundError(Exception):
    """The requested resource does not exist (404)."""


class ConflictError(Exception):
    """The change would clash with existing data (409)."""


class RestaurantNotFoundError(NotFoundError):
    def __init__(self, restaurant_id: int):
        super().__init__(f"Restaurant {restaurant_id} not found")


class EmptyUpdateError(BadRequestError):
    def __init__(self):
        super().__init__("Update request must include at least one field")
