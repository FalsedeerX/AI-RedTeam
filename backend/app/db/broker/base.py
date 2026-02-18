from collections.abc import Sequence
from typing import TypeVar, Generic, Type, Optional, Any, cast
from sqlalchemy import select, delete, update
from sqlalchemy.engine import CursorResult
from app.db.session import get_session


T = TypeVar("T")


class BaseBroker(Generic[T]):
    """ Generic CRUD broker for each table entry """
    def __init__(self, model: Type[T]):
        self.model = model

    def get(self, primary_key: Any) -> Optional[T]:
        """ Retrieve entry by primary key, return selected entry """
        with get_session() as session:
            return session.get(self.model, primary_key)

    def get_bulk(self, filters: dict[str, Any]) -> Sequence[T]:
        """ Query in bulk by custom filters in dictionary, return selected entries in sequence """
        with get_session() as session:
            query = select(self.model).filter_by(**filters)
            return session.scalars(query).all()

    def create(self, data: dict[str, Any]) -> T:
        """ Create a new entry in the table by the attributes specified in dictionary, return created entry """
        with get_session() as session:
            entry = self.model(**data)
            session.add(entry)
            session.flush()
            session.refresh(entry)
            return entry

    def apply(self, primary_key: Any, values: dict[str, Any]) -> Optional[T]:
        """ Update a single entry via the provided primary key, return modified entry """
        if not values: return None
        with get_session() as session:
            entry = session.get(self.model, primary_key)
            if not entry: return None
            for key, value in values.items():
                if hasattr(self.model, key):
                    setattr(entry, key, value)

            session.flush()
            session.refresh(entry)
            return entry

    def apply_bulkj(self, filters: dict[str, Any], values: dict[str, Any]) -> int:
        """ Update in bulk by custom filters in dictionary, return total updated rows count """
        if not values: return 0
        if not filters: raise ValueError("Refuse to update without filters")
        with get_session() as session:
            stmt = update(self.model).filter_by(**filters).values(**values)
            result = cast(CursorResult, session.execute(stmt))
            return result.rowcount or 0

    def purge(self, primary_key: Any) -> bool:
        """ Delete entry by primary key """
        with get_session() as session:
            entry = session.get(self.model, primary_key)
            if not entry: return False
            session.delete(entry)
            return True

    def purge_bulk(self, filters: dict[str, Any]) -> int:
        """ Delete in bulk by cusotm filters in dictionary, return total deleted rows count """
        if not filters: raise ValueError("Refuse to purge without filters")
        with get_session() as session:
            stmt = delete(self.model).filter_by(**filters)
            result = cast(CursorResult, session.execute(stmt))
            return result.rowcount or 0
