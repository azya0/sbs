from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Ingredient
from routers.schemas import IngredientGet, IngredientPatch, IngredientPost
from db.engine import get_async_session


router = APIRouter(
    prefix="/ingredient",
    tags=["ingredient"],
)


@router.post('/', response_model=IngredientGet)
async def add_new_ingredient(data: IngredientPost, session: AsyncSession = Depends(get_async_session)):
    ingredient = Ingredient(**data.model_dump())

    session.add(ingredient)
    await session.commit()
    await session.refresh(ingredient)

    return ingredient


@router.get('/all', response_model=list[IngredientGet])
async def get_all_ingredients(session: AsyncSession = Depends(get_async_session)):
    return (await session.scalars(select(Ingredient))).all()


@router.patch('/{id}', response_model=IngredientGet)
async def change_ingredient_count(id: int, data: IngredientPatch, session: AsyncSession = Depends(get_async_session)):
    ingredient = await session.get(Ingredient, id)
    
    if ingredient is None:
        raise HTTPException(404, 'no ingredient with such id')

    if data.available is not None:
        if data.available < 0:
            raise HTTPException(400, 'wrong new_count value')

        ingredient.available = data.available

    if data.name is not None:
        ingredient.name = data.name

    session.add(ingredient)
    await session.commit()
    await session.refresh(ingredient)

    return ingredient


@router.delete('/{id}')
async def delete_ingredient(session: AsyncSession = Depends(get_async_session)):
    ingredient = await session.get(Ingredient, id)

    if ingredient is None:
        raise HTTPException(404, 'wrong ingredient id')
    
    await session.delete(ingredient)
