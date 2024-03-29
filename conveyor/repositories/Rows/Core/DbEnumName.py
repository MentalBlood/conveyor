import dataclasses

from ....core import Item, Transforms


@dataclasses.dataclass(frozen=True, kw_only=False)
class DbEnumName(Transforms.Safe[Item.Key, str]):
    postfix: str

    def transform(self, i: Item.Key) -> str:
        return f"{i.value}_{self.postfix}"

    def __invert__(self) -> "ItemKey":
        return ItemKey(self.postfix)


@dataclasses.dataclass(frozen=True, kw_only=False)
class ItemKey(Transforms.Safe[str, Item.Key]):
    postfix: str

    def transform(self, i: str) -> Item.Key:
        return Item.Key(i[: -len(self.postfix) - 1])

    def __invert__(self) -> DbEnumName:
        return DbEnumName(self.postfix)
