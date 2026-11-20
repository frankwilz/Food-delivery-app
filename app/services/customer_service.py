from app.core.errors import ConflictError, EmptyUpdateError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.repositories.customer_repository import CustomerRepository
from app.repositories.json_repository import transaction
from app.schemas.customer import CustomerCreate, CustomerUpdate


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
        fields = data.model_dump(exclude={"password"})
        # Only the salted hash is stored; the plain-text password goes no further than here.
        # Hashed before taking the lock, because hashing is deliberately slow
        password_hash = hash_password(data.password)
        # The email check and the save are one step, so two sign-ups with the same email cannot both succeed
        with transaction(self.repository):
            if self.repository.get_by_email(data.email) is not None:
                raise DuplicateEmailError(data.email)
            return self.repository.create(
                {
                    **fields,
                    "password_hash": password_hash,
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

    def update_profile(self, customer_id: int, changes: CustomerUpdate) -> dict:
        """Change the customer's name, email and/or delivery address, and return the updated account.

        `CustomerUpdate` only has those three fields and forbids any other, so `id`, `role`,
        `is_active` and the password hash can never be changed here (422 before this runs).
        """
        fields = changes.model_dump(exclude_unset=True)
        if not fields:
            raise EmptyUpdateError()
        with transaction(self.repository):
            self.get_active_customer(customer_id)
            if "email" in fields:
                # Unique ignoring case, like registration; changing only the case of your own email is fine
                owner = self.repository.get_by_email(fields["email"])
                if owner is not None and owner["id"] != customer_id:
                    raise DuplicateEmailError(fields["email"])
            return self.repository.update(customer_id, fields)

    def deactivate(self, customer_id: int) -> dict:
        """Deactivate an account. The record is kept, so the email stays taken and orders keep their owner.

        From then on the customer cannot log in, and tokens issued before are refused (both 403).
        """
        with transaction(self.repository):
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
