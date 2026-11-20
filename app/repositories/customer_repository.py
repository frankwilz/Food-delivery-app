from app.repositories.json_repository import JsonRepository


class CustomerRepository(JsonRepository):
    """The only code allowed to read or write data/customers.json."""

    def get_by_id(self, customer_id: int) -> dict | None:
        for customer in self.get_all():
            if customer["id"] == customer_id:
                return customer
        return None

    def get_by_email(self, email: str) -> dict | None:
        # Emails are matched ignoring case, so "Ana@Example.com" finds "ana@example.com"
        wanted = email.strip().casefold()
        for customer in self.get_all():
            if customer["email"].strip().casefold() == wanted:
                return customer
        return None

    def create(self, customer_data: dict) -> dict:
        with self.lock:
            customers = self.get_all()
            # The new record is only appended; existing customers are never overwritten
            new_customer = {"id": self.next_id(customers), **customer_data}
            customers.append(new_customer)
            self.save(customers)
            return new_customer

    def update(self, customer_id: int, changes: dict) -> dict | None:
        with self.lock:
            customers = self.get_all()
            for customer in customers:
                if customer["id"] == customer_id:
                    # The id is never overwritten, so carts and orders keep pointing at the right customer.
                    # Which other fields may change is decided by CustomerService, not here.
                    customer.update({key: value for key, value in changes.items() if key != "id"})
                    self.save(customers)
                    return customer
            return None
