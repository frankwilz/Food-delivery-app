from app.core.errors import UnauthorizedError
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.repositories.customer_repository import CustomerRepository
from app.services.customer_service import ensure_active

# Checked when the email is unknown, so that case takes as long as a wrong password
# and the response time does not reveal which emails have accounts
DUMMY_PASSWORD_HASH = hash_password("no-account-uses-this-password")


class InvalidCredentialsError(UnauthorizedError):
    def __init__(self):
        # One message for both cases, so the response does not reveal which emails have accounts
        super().__init__("Incorrect email or password")


class NotAuthenticatedError(UnauthorizedError):
    def __init__(self):
        super().__init__("Not authenticated")


class InvalidTokenError(UnauthorizedError):
    def __init__(self):
        super().__init__("Invalid or expired token")


class AuthService:
    """Login and token checks. Routes call this; this calls the customer repository."""

    def __init__(self, repository: CustomerRepository):
        self.repository = repository

    def login(self, email: str, password: str) -> str:
        customer = self.repository.get_by_email(email)
        password_hash = customer["password_hash"] if customer else DUMMY_PASSWORD_HASH
        if not verify_password(password, password_hash) or customer is None:
            raise InvalidCredentialsError()
        # Checked only after the password is right, so a wrong password never reveals the account's status
        ensure_active(customer)
        return create_access_token(customer["id"])

    def get_customer_for_token(self, token: str) -> dict:
        """Return the active customer a token belongs to: 401 if the token is bad, 403 if deactivated."""
        customer_id = decode_access_token(token)
        customer = self.repository.get_by_id(customer_id) if customer_id is not None else None
        if customer is None:
            raise InvalidTokenError()
        # The account is read on every request, so a token issued before deactivation stops working at once
        return ensure_active(customer)
