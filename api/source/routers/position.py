from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Row, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import Ingredient, Position, Position_xref_Ingredient
from routers.schemas import (
    IngredientFull, IngredientPostForPosition, IngredientPostForPositionRead, PositionAvailable, PositionBase,
    PositionGet, PositionGetFull, PositionId, PositionPatch, PositionPost, PositionWithAvailability, PositionsAvailable
)
from db.engine import get_async_session


router = APIRouter(
    prefix="/position",
    tags=["position"],
)


@router.post('/', response_model=PositionGet)
async def add_new_position(data: PositionPost, session: AsyncSession = Depends(get_async_session)):
    position = (await session.scalar(select(Position).where(Position.name == data.name)))

    if position is not None:
        raise HTTPException(400, "position with such name already exist")
    
    ingredients: list[tuple[Ingredient, int]] = []
    if data.ingredients_id is not None and len(data.ingredients_id):
        for ingredient_data in data.ingredients_id:
            ingredient = await session.get(Ingredient, ingredient_data.id)

            if ingredient is None:
                raise HTTPException(404, "wrong ingredient id")

            ingredients.append((ingredient, ingredient_data.count))

    delattr(data, "ingredients_id")
    position = Position(**data.model_dump())

    session.add(position)
    await session.commit()
    await session.refresh(position)

    for ingredient, count in ingredients:
        session.add(
            Position_xref_Ingredient(
                position_id=position.id,
                ingredient_id=ingredient.id,
                count=count,
        ))

    await session.commit()

    return PositionGet(
        id=position.id,
        name=position.name,
        description=position.description,
        is_changable=position.is_changable,
        cost=position.cost,
        ingredients=map(lambda pair: IngredientPostForPosition(
            id=pair[0].id,
            name=pair[0].name,
            count=pair[1]
        ), ingredients)
    )


@router.get('/all', response_model=list[PositionGet])
async def get_all_positions(session: AsyncSession = Depends(get_async_session)):
    positions = (await session.scalars(select(Position))).all()

    result = []
    for position in positions:
        query = select(Ingredient.id, Ingredient.name, Position_xref_Ingredient.count)
        query = query.select_from(Position_xref_Ingredient)
        query = query.join(Ingredient, Position_xref_Ingredient.ingredient_id == Ingredient.id)
        query = query.where(Position_xref_Ingredient.position_id == position.id)

        ingredients_data = (await session.execute(query)).all()

        result.append(PositionGet(
            id=position.id,
            ingredients=map(
                lambda data: IngredientPostForPosition(**data._mapping),
                ingredients_data
            ),
            **PositionBase.model_validate(position).model_dump()
        ))

    return result


@router.delete('/{id}')
async def delete_position(id: int, session: AsyncSession = Depends(get_async_session)):
    position = await session.get(Position, id)

    if position is None:
        raise HTTPException(404, "no position with such id")

    query = select(Position_xref_Ingredient).where(Position_xref_Ingredient.position_id == position.id)

    for connection in (await session.scalars(query)).all():
        await session.delete(connection)
    
    await session.delete(position)


@router.patch('/{id}', response_model=PositionId)
async def patch_position(id: int, data: PositionPatch, session: AsyncSession = Depends(get_async_session)):
    position = await session.get(Position, id)

    if position is None:
        raise HTTPException(404, "no position with such id")

    for key in (data := data.model_dump(exclude_none=True)):
        setattr(position, key, data[key])
    
    session.add(position)
    await session.commit()

    result = PositionId.model_validate(position)

    return result


@router.put('/{id}/ingredients', response_model=PositionGet)
async def patch_position_ingredients(id: int, data: list[IngredientPostForPositionRead], session: AsyncSession = Depends(get_async_session)):
    position = await session.get(Position, id)

    if position is None:
        raise HTTPException(404, "no position with such id")

    query = select(Position_xref_Ingredient).where(
        Position_xref_Ingredient.position_id == id
    ).order_by(Position_xref_Ingredient.ingredient_id)
    connections: list[Position_xref_Ingredient] = (await session.scalars(query)).all()

    def binary_search(array: list[Position_xref_Ingredient], _id: int) -> Position_xref_Ingredient | None:
        start, end = 0, len(array) - 1

        while end >= start:
            index = (start + end) // 2

            if (obj := array[index]).ingredient_id == _id:
                return obj
            
            if obj.ingredient_id > _id:
                start = index + 1
            else:
                end = index - 1
        
        return None

    # list of turple of Ingredient, number of ingredients in position 
    # and aleready existing connection in database
    new_ingredients: list[tuple[Ingredient, int, bool]] = []

    for ingredient_data in data:
        ingredient = await session.get(Ingredient, ingredient_data.id)

        if ingredient is None:
            raise HTTPException(400, "wrong ingredient id")
        
        search_result = binary_search(connections, ingredient.id)

        if (already := search_result is not None):
            if search_result.count != ingredient_data.count:
                search_result.count = ingredient_data.count
                session.add(search_result)

            connections.remove(search_result)
    
        new_ingredients.append((ingredient, ingredient_data.count, already))
    
    for ingredient, count, already in new_ingredients:
        if already:
            continue

        session.add(
            Position_xref_Ingredient(
                position_id=position.id,
                ingredient_id=ingredient.id,
                count=count
        ))

    await session.commit()
    
    for connection in connections:
        await session.delete(connection)
    
    return PositionGet(
        id=position.id,
        **PositionBase.model_validate(position).model_dump(),
        ingredients=map(lambda struct: IngredientPostForPosition(
            id=struct[0].id,
            name=struct[0].name,
            count=struct[1]
        ), new_ingredients)
    )


async def get_position_data(position_id: int, session: AsyncSession) -> list[Row]:
    query = select(Ingredient.id, Ingredient.name, Ingredient.available, Position_xref_Ingredient.count)
    query = query.select_from(Position_xref_Ingredient)
    query = query.join(Ingredient, Position_xref_Ingredient.ingredient_id == Ingredient.id)
    query = query.where(Position_xref_Ingredient.position_id == position_id)

    return (await session.execute(query)).all()


async def sort_ingredient_data(ingredients_data: list[Row]) -> tuple[list[IngredientFull], list[IngredientFull], int]:
    number: float = float('+inf')
    available_ingredients: list[IngredientFull] = []
    unavailable_ingredients: list[IngredientFull] = []

    for ingredient_data in ingredients_data:
        current = ingredient_data.available // ingredient_data.count
        ingredient = IngredientFull.model_validate(ingredient_data)

        if current == 0:
            unavailable_ingredients.append(ingredient)
        else:
            available_ingredients.append(ingredient)
        
        number = min(number, current)
    
    if number == float('inf'):
        number = -1

    return available_ingredients, unavailable_ingredients, int(number)


@router.get('/availability/{id}', response_model=PositionAvailable)
async def get_available_position(id: int, session: AsyncSession = Depends(get_async_session)):
    position = await session.get(Position, id)

    if position is None:
        raise HTTPException(400, 'no position with such id')

    ingredients_data = await get_position_data(position.id, session)

    _, unavailable_ingredients, number = await sort_ingredient_data(ingredients_data)

    return PositionAvailable(
        avalible=number,
        unavailable_ingredients=unavailable_ingredients,
        **PositionId.model_validate(position).model_dump()
    )


@router.get('/all/availability', response_model=PositionsAvailable)
async def get_all_available_position(session: AsyncSession = Depends(get_async_session)):
    positions = (await session.scalars(select(Position))).all()

    available_positions: list[tuple[Position, int, list[IngredientFull]]] = []
    unavailable_positions: list[tuple[Position, list[IngredientFull], list[IngredientFull]]] = []

    for position in positions:
        ingredients_data = await get_position_data(position.id, session)

        available_ingredients, unavailable_ingredients, number = await sort_ingredient_data(ingredients_data)
        
        if number == 0:
            unavailable_positions.append((position, available_ingredients, unavailable_ingredients))
        else:
            available_positions.append((position, number, available_ingredients))

    return PositionsAvailable(
        available=map(lambda struct: PositionGetFull(
            available=struct[1],
            ingredients=struct[2],
            **PositionId.model_validate(struct[0]).model_dump()
        ), available_positions),
        unavailable=map(lambda struct: PositionWithAvailability(
            available_ingredients=struct[1],
            unavailable_ingredients=struct[2],
            **PositionId.model_validate(struct[0]).model_dump()
        ), unavailable_positions)
    )
