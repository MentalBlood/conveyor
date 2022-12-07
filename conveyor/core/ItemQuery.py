import pydantic

from .ItemMask import ItemMask



@pydantic.dataclasses.dataclass(frozen=True, kw_only=True)
class ItemQuery:

	mask: ItemMask
	limit: int | None

	@pydantic.validator('limit')
	def limit_correct(cls, limit):
		if limit is not None:
			if limit <= 0:
				raise ValueError(f"Query result limit must be greater then 0 (received {limit} <= 0)")