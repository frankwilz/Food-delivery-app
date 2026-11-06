from app.repositories.json_repository import JsonRepository


class CustomerRepository(JsonRepository):
    """The only code allowed to read or write data/customers.json."""

    def get_by_email(self, email: str) -> dict | None:
        # Emails are matched ignoring case, so "Ana@Example.com" finds "ana@example.com"
        wanted = email.strip().casefold()
        for customer in self.get_all():
            if customer["email"].strip().casefold() == wanted:
                return customer
        return None

    def create(self, customer_data: dict) -> dict:
        customers = self.get_all()
        # The new record is only appended; existing customers are never overwritten
        new_customer = {"id": self.next_id(customers), **customer_data}
        customers.append(new_customer)
        self.save(customers)
        return new_customer
