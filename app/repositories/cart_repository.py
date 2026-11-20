from app.repositories.json_repository import JsonRepository


class CartRepository(JsonRepository):
    """The only code allowed to read or write data/carts.json."""

    def get_by_id(self, cart_id: int) -> dict | None:
        for cart in self.get_all():
            if cart["id"] == cart_id:
                return cart
        return None

    def get_active_for_customer(self, customer_id: int) -> dict | None:
        for cart in self.get_all():
            if cart["customer_id"] == customer_id and cart["status"] == "active":
                return cart
        return None

    def create(self, cart_data: dict) -> dict:
        with self.lock:
            carts = self.get_all()
            new_cart = {"id": self.next_id(carts), **cart_data}
            carts.append(new_cart)
            self.save(carts)
            return new_cart

    def update(self, cart_id: int, changes: dict) -> dict | None:
        with self.lock:
            carts = self.get_all()
            for cart in carts:
                if cart["id"] == cart_id:
                    # The id and owner are never overwritten
                    cart.update({k: v for k, v in changes.items() if k not in ("id", "customer_id")})
                    self.save(carts)
                    return cart
            return None
