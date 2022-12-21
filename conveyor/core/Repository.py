import typing
import pydantic
import functools
import itertools
import dataclasses

from . import Item, ItemQuery, ItemPart, PartRepository



Parts = typing.Sequence[PartRepository]


@dataclasses.dataclass(frozen=True, kw_only=False)
class Repository:

	Parts = Parts

	parts: Parts

	@pydantic.validator('parts')
	def parts_valid(cls, parts: Parts) -> Parts:
		if len(parts) < 1:
			raise ValueError(f'Repository must have at least 1 part ({len(parts)} provided)')
		return parts

	@pydantic.validate_arguments
	def add(self, item: Item) -> None:
		for p in reversed(self.parts):
			p.add(item)

	@pydantic.validate_arguments
	def _get(self, query: ItemQuery, repositories: typing.Sequence[PartRepository], parts: typing.Iterable[ItemPart] = (ItemPart(),)) -> typing.Iterable[Item]:

		if not len(repositories):
			for p in parts:
				yield p.item
			return

		for p in parts:
			for item in self._get(
				query=query,
				repositories=repositories[1:],
				parts=repositories[0].get(query, p)
			):
				yield item

	@pydantic.validate_arguments
	def __getitem__(self, item_query: ItemQuery) -> typing.Iterable[Item]:

		reserver = Item.Reserver(exists=True)

		for i in [*itertools.islice(
			self._get(
				query=dataclasses.replace(
					item_query,
					mask=dataclasses.replace(
						item_query.mask,
						reserver=Item.Reserver(exists=False)
					)
				),
				repositories=self.parts
			),
			item_query.limit
		)]:
			i_reserved = dataclasses.replace(i, reserver=reserver)
			try:
				self.__setitem__(i, i_reserved, True)
			except KeyError:
				raise
				continue
			yield i_reserved

	@pydantic.validate_arguments
	def __setitem__(self, old: Item, new: Item, for_reserve: bool = False) -> None:
		if not for_reserve:
			new = dataclasses.replace(new, reserver=Item.Reserver(exists=False))
		for p in reversed(self.parts):
			p[old] = new

	@pydantic.validate_arguments
	def __delitem__(self, item: Item) -> None:
		for p in self.parts:
			try:
				del p[item]
			except KeyError:
				break

	@pydantic.validate_arguments
	def transaction(self, f: typing.Callable) -> typing.Callable:
		return functools.reduce(lambda result, t: t.transaction(result), reversed(self.parts), f)