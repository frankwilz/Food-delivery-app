from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerCreate


class DuplicateEmailError(ConflictError):
    def __init__(self, email: str):
        super().__init__(f"An account with email '{email}' already exists")


class CustomerNotFoundError(NotFoundError):
    def __init__(self, customer_id: int):
        super().__init__(f"Customer {customer_id} not found")


class CustomerDeactivatedError(ForbiddenError):
    def __init__(self, customer_id: int):
        super().__init__(f"Customer {customer_id} has been deactivated")


class CustomerService:
    """Business rules for customer accounts. Routes call this; this calls the repository."""

    def __init__(self, repository: CustomerRepository):
        self.repository = repository

    def register(self, data: CustomerCreate) -> dict:
        if self.repository.get_by_email(data.email) is not None:
            raise DuplicateEmailError(data.email)
        fields = data.model_dump(exclude={"password"})
        # Only the salted hash is stored; the plain-text password goes no further than here
        return self.repository.create(
            {
                **fields,
                "password_hash": hash_password(data.password),
                "role": "customer",  # self-registration can never create a manager
                "is_active": True,
            }
        )

    def get_active_customer(self, customer_id: int) -> dict:
        """Return the customer if the account exists and is active, otherwise raise a clear error.

        This is the single rule for "may this customer use the app?". The cart and checkout
        call it instead of checking `is_active` themselves.
        """
        customer = self.repository.get_by_id(customer_id)
        if customer is None:
            raise CustomerNotFoundError(customer_id)
        return ensure_active(customer)

    def deactivate(self, customer_id: int) -> dict:
        """Deactivate an account. The record is kept, so the email stays taken and orders keep their owner.

        From then on the customer cannot log in, and tokens issued before are refused (both 403).
        """
        if self.repository.get_by_id(customer_id) is None:
            raise CustomerNotFoundError(customer_id)
        return self.repository.update(customer_id, {"is_active": False})


def ensure_active(customer: dict) -> dict:
    """Return the customer if the account is active, otherwise raise `CustomerDeactivatedError` (403).

    Shared by `CustomerService.get_active_customer` and the login and token checks in
    `AuthService`, so "is this account active?" is decided in one place.
    """
    if not customer["is_active"]:
        raise CustomerDeactivatedError(customer["id"])
    return customer
