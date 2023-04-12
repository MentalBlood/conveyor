from ....core import Item as Item, Transforms as Transforms

class DbTableName(Transforms.Safe[Item.Type, str]):
    prefix: str
    def transform(self, i: Item.Type) -> str: ...
    def __invert__(self) -> ItemType: ...

class ItemType(Transforms.Safe[str, Item.Type]):
    prefix: str
    def transform(self, i: str) -> Item.Type: ...
    def __invert__(self) -> DbTableName: ...
