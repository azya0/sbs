import datetime
import enum

from sqlalchemy import Column, Enum, String, Integer, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import as_declarative, relationship


@as_declarative()
class Base:
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)


class Ingredient(Base):
    __tablename__ = 'ingredient'

    name = Column(String(64), nullable=False, unique=True)
    available = Column(Integer, default=0, nullable=False)

    positions = relationship('Position', secondary='position_xref_ingredient', back_populates='ingredients', uselist=True)


class Position(Base):
    __tablename__ = 'position'

    name = Column(String(64), nullable=False, unique=True)
    description = Column(String(512), nullable=True)
    is_changable = Column(Boolean, default=False, nullable=False)
    cost = Column(Integer, nullable=False)

    ingredients = relationship('Ingredient', secondary='position_xref_ingredient', back_populates='positions', uselist=True)
    orders = relationship('Order', secondary='position_xref_order', back_populates='positions', uselist=True)
    
class Position_xref_Ingredient(Base):
    __tablename__ = 'position_xref_ingredient'

    position_id = Column(Integer, ForeignKey('position.id'), index=True, nullable=False)
    ingredient_id = Column(Integer, ForeignKey('ingredient.id'), nullable=False)
    count = Column(Integer, nullable=False)


class OrderStatus(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    PROGRESS = "PROGRESS"
    READY = "READY"
    ISSUED = "ISSUED"


class Order(Base):
    __tablename__ = 'order'

    table_id = Column(Integer, nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.ACCEPTED, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        onupdate=datetime.datetime.now
    )
    ended_at = Column(DateTime(timezone=True), nullable=True)

    positions = relationship('Position', secondary='position_xref_order', back_populates='orders', uselist=True)


class Position_xref_Order(Base):
    __tablename__ = 'position_xref_order'

    order_id = Column(Integer, ForeignKey('order.id'), index=True, nullable=False)
    position_id = Column(Integer, ForeignKey('position.id'), nullable=False)
    count = Column(Integer, nullable=False)
