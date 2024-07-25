import datetime
from pydantic import BaseModel, field_validator, model_validator

from db.models import OrderStatus


class AtLeastOneValidator:
    @model_validator(mode="after")
    def at_least_one_field(self: BaseModel):
        if all(tuple(map(lambda value: value is None, self.model_dump().values()))):
            raise ValueError("All fields can't be null")
        return self


class IngredientPost(BaseModel):
    name: str
    available: int | None = None


class IngredientGet(IngredientPost):
    id: int 
    available: int

    class Config:
        from_attributes = True


class IngredientPatch(BaseModel, AtLeastOneValidator):
    name: str | None = None
    available: int | None = None



class PositionBase(BaseModel):
    name: str
    description: str | None = None
    is_changable: bool
    cost: int

    class Config:
        from_attributes = True


class PositionId(PositionBase):
    id: int


class IngredientPostForPositionRead(BaseModel):
    id: int
    count: int


class IngredientPostForPosition(IngredientPostForPositionRead):
    name: str

    class Config:
        from_attributes = True


class IngredientFull(IngredientPostForPosition):
    available: int

    class Config:
        from_attributes = True


class PositionPost(PositionBase):
    is_changable: bool | None = None
    ingredients_id: list[IngredientPostForPositionRead] | None = None


class PositionGet(PositionId):
    ingredients: list[IngredientPostForPosition]


class PositionFull(PositionId):
    count: int
    ingredients: list[IngredientFull]


class PositionShort(PositionId):
    count: int


class PositionGetFull(PositionFull):
    available: int


class PositionWithAvailability(PositionId):
    available_ingredients: list[IngredientFull]
    unavailable_ingredients: list[IngredientFull]


class PositionPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    is_changable: bool | None = None
    cost: int | None = None


class PositionAvailable(PositionId):
    avalible: int
    unavailable_ingredients: list[IngredientFull]


class PositionsAvailable(BaseModel):
    available: list[PositionGetFull]
    unavailable: list[PositionWithAvailability]


class OrderPosition(BaseModel):
    id: int
    count: int

    @field_validator('count')
    @classmethod
    def count_checker(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("count can't be zero or lower")
        return value


class PositionInOrder(PositionId):
    count: int


class OrderBase(BaseModel):
    id: int
    table_id: int
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    ended_at: datetime.datetime | None = None

    class Config:
        from_attributes = True


class OrderPatch(BaseModel, AtLeastOneValidator):
    table_id: int | None = None
    status: OrderStatus | None = None
    ended_at: datetime.datetime | None = None


class OrderGet(OrderBase):
    cost: int
    positions: list[PositionFull]


class OrderGetShort(OrderGet):
    positions: list[PositionShort]
