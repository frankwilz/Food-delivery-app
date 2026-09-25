from pydantic import BaseModel


class Restaurant(BaseModel):
    id: int
    name: str
    cuisine: str
    address: str
    rating: float
    is_open: bool