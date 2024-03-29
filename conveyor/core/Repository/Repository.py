import typing
import contextlib
import dataclasses

from ..Item.Part import Part
from .Query import Query
from ..Item.Item import Item
from .PartRepository import PartRepository


@dataclasses.dataclass(frozen=True, kw_only=False)
class Repository:
    Parts = typing.Sequence[PartRepository]

    parts: Parts
    transaction_: bool = False

    def __post_init__(self):
        if not self.parts:
            raise ValueError("`parts` must contain at least one element")

    def _unreserved(self, item: Item) -> Item:
        return dataclasses.replace(item, reserver=Item.Reserver(None))

    def append(self, item: Item) -> None:
        for p in reversed(self.parts):
            p.append(self._unreserved(item))

    def _get(
        self,
        query: Query,
        repositories: typing.Sequence[PartRepository],
        parts: typing.Iterable[Part] | None = None,
    ) -> typing.Iterable[Item]:
        parts = parts or (Part(),)
        if repositories:
            for p in parts:
                yield from self._get(
                    query=query,
                    repositories=repositories[1:],
                    parts=repositories[0].get(query, p),
                )
        else:
            for p in parts:
                yield p.item

    def __getitem__(self, item_query: Query) -> typing.Iterable[Item]:
        reserver = Item.Reserver()
        got: int = 0

        for i in self._get(
            query=dataclasses.replace(
                item_query,
                mask=dataclasses.replace(item_query.mask, reserver=Item.Reserver(None)),
            ),
            repositories=self.parts,
        ):
            reserved = dataclasses.replace(i, reserver=reserver)
            try:
                self._setitem(i, reserved)
            except KeyError:
                continue

            yield reserved
            got += 1
            if got == item_query.limit:
                break

    def _setitem(self, old: Item, new: Item):
        with self.transaction() as t:
            for p in reversed(t.parts):
                try:
                    p[old] = new
                except NotImplementedError:
                    """"""

    def __setitem__(self, old: Item, new: Item) -> None:
        self._setitem(old, self._unreserved(new))

    def __delitem__(self, item: Item) -> None:
        with self.transaction() as t:
            for p in t.parts:
                try:
                    del p[item]
                except KeyError:
                    break

    @contextlib.contextmanager
    def _transaction(
        self, parts_to_include: typing.Sequence[PartRepository]
    ) -> typing.Iterator[typing.Sequence[PartRepository]]:
        match len(parts_to_include):
            case 0:
                yield ()
            case _:
                with parts_to_include[0].transaction() as t, self._transaction(
                    parts_to_include[1:]
                ) as _t:
                    yield (t, *_t)

    @contextlib.contextmanager
    def transaction(self) -> typing.Iterator[typing.Self]:
        match self.transaction_:
            case True:
                yield self
            case False:
                with self._transaction(self.parts) as transaction_parts:
                    yield dataclasses.replace(
                        self, parts=transaction_parts, transaction_=True
                    )

    def __len__(self) -> int:
        return max(len(p) for p in self.parts)

    def clear(self) -> None:
        with self.transaction() as t:
            for p in t.parts:
                p.clear()
