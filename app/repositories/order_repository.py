from app.repositories.json_repository import JsonRepository


class OrderRepository(JsonRepository):
    """The only code allowed to read or write data/orders.json."""

    def get_by_id(self, order_id: int) -> dict | None:
        for order in self.get_all():
            if order["id"] == order_id:
                return order
        return None

    def get_by_customer(self, customer_id: int) -> list[dict]:
        return [order for order in self.get_all() if order["customer_id"] == customer_id]

    def get_by_cart_id(self, cart_id: int) -> dict | None:
        for order in self.get_all():
            if order.get("cart_id") == cart_id:
                return order
        return None

    def create(self, order_data: dict) -> dict:
        with self.lock:
            orders = self.get_all()
            # Orders are only ever appended, so an order's id and contents never change once saved
            new_order = {"id": self.next_id(orders), **order_data}
            orders.append(new_order)
            self.save(orders)
            return new_order
