import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Row, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Order, OrderStatus, Position, Position_xref_Order
from routers.position import get_position_data
from routers.schemas import (
    OrderBase, OrderGet, OrderGetShort, OrderPatch, OrderPosition, PositionFull, PositionId
)
from db.engine import get_async_session


router = APIRouter(
    prefix="/order",
    tags=["order"],
)


@router.post('/', response_model=OrderGet)
async def post_order(table_id: int, data: list[OrderPosition], session: AsyncSession = Depends(get_async_session)):
    positions: list[tuple[Position, int, list[Row]]] = []
    cost: int = 0

    for position_data in data:
        position = await session.get(Position, position_data.id)

        if position is None:
            raise HTTPException(400, "wrong position id")
        
        ingredients_data = await get_position_data(position.id, session)
        
        available_ingredients: list[Row] = []
        for ingredient_data in ingredients_data:
            if (ingredient_data.count * position_data.count) > ingredient_data.available:
                raise HTTPException(400, f"no ingredients for position {position.id}")

            available_ingredients.append(ingredient_data)

        positions.append((position, position_data.count, ingredients_data))
        cost += position.cost * position_data.count

    order = Order(table_id=table_id)
    
    session.add(order)
    await session.commit()
    await session.refresh(order)

    for position, count, _ in positions:
        session.add(Position_xref_Order(
            order_id=order.id,
            position_id=position.id,
            count=count
        ))

    await session.commit()

    return OrderGet(
        cost=cost,
        positions=map(
            lambda struct: PositionFull(
                **PositionId.model_validate(struct[0]).model_dump(),
                count=struct[1],
                ingredients=struct[2]
            ),
            positions
        ),
        **OrderBase.model_validate(order).model_dump()
    )


async def get_order_data(order_id: int, session: AsyncSession) -> list[Row]:
    query = select(Position.__table__.columns, Position_xref_Order.count)
    query = query.select_from(Position_xref_Order)
    query = query.join(Position, Position_xref_Order.position_id == Position.id)
    query = query.where(Position_xref_Order.order_id == order_id)

    return (await session.execute(query)).all()


async def get_full_order_data(orders: list[Order], session: AsyncSession) -> list[tuple[Order, int, Row]]:
    result: list[tuple[Order, int, Row]] = []

    for order in orders:
        cost: int = 0
        order_data = await get_order_data(order.id, session)

        for position in order_data:
            cost += (position.cost * position.count)

        result.append((order, cost, order_data))
    
    return result


@router.get('/all', response_model=list[OrderGetShort])
async def get_orders(session: AsyncSession = Depends(get_async_session)):
    orders = (await session.scalars(select(Order))).all()

    result = await get_full_order_data(orders, session)

    return [
        OrderGetShort(
            **OrderBase.model_validate(order).model_dump(),
            cost=cost,
            positions=order_data
        ) for order, cost, order_data in result]


@router.get('/all/current', response_model=list[OrderGetShort])
async def get_current_orders(session: AsyncSession = Depends(get_async_session)):
    orders = (await session.scalars(select(Order).where(Order.status != OrderStatus.ISSUED))).all()

    result = await get_full_order_data(orders, session)

    return [
        OrderGetShort(
            **OrderBase.model_validate(order).model_dump(),
            cost=cost,
            positions=order_data
        ) for order, cost, order_data in result]


@router.patch('/{id}', response_model=OrderBase)
async def patch_order(id: int, data: OrderPatch, session: AsyncSession = Depends(get_async_session)):
    order = await session.get(Order, id)

    if order is None:
        raise HTTPException(404, "no order with such id")

    if data.status == OrderStatus.ISSUED:
        order.ended_at = datetime.datetime.now()

    for key in (dumped_data := data.model_dump(exclude_none=True)):
        setattr(order, key, dumped_data[key])

    session.add(order)
    await session.commit()
    await session.refresh(order)

    return order
