from app.core.errors import ConflictError
from app.core.security import hash_password
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerCreate


class DuplicateEmailError(ConflictError):
    def __init__(self, email: str):
        super().__init__(f"An account with email '{email}' already exists")


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
