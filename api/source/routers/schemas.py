from pydantic import BaseModel, model_validator


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


class IngredientFull(IngredientPostForPosition):
    available: int

    class Config:
        from_attributes = True


class PositionPost(PositionBase):
    is_changable: bool | None = None
    
    ingredients_id: list[IngredientPostForPosition] | None = None


class PositionGet(PositionId):
    ingredients: list[IngredientPostForPosition]


class PositionGetFull(PositionId):
    available: int

    ingredients: list[IngredientFull]


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
