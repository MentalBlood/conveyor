import typing
import itertools
import sqlalchemy
import dataclasses
import sqlalchemy.exc

from .....core import Transforms, Item

from .. import Cache
from ..Connect import Connect
from ..DbTableName import DbTableName

from .Columns import columns


@dataclasses.dataclass(frozen=True, kw_only=True)
class EnumsTransform:
    connect: Connect
    enum_table: str
    cache_id: str

    @property
    def cache(self) -> Cache.Enums.Cache:
        return Cache.cache[self.cache_id]

    def load(self) -> None:
        self.cache.load(self.enum_table, self.connect)


@dataclasses.dataclass(frozen=True, kw_only=True)
class Integer(EnumsTransform, Transforms.Trusted[Item.Metadata.Enumerable, int]):
    @property
    def table(self):
        return sqlalchemy.Table(self.enum_table, sqlalchemy.MetaData(), *columns())

    def transform(self, i: Item.Metadata.Enumerable) -> int:
        try:
            return self.cache[self.enum_table].value[Item.Metadata.Enumerable(i.value)]
        except KeyError:
            """"""

        try:
            self.load()
            return self.cache[self.enum_table].value[Item.Metadata.Enumerable(i.value)]
        except Exception:
            """"""

        try:
            with self.connect() as connection:
                value = connection.execute(
                    sqlalchemy.text(
                        f"insert into {self.enum_table} (description) "
                        f"values ('{i.value}') returning value"
                    )
                ).scalar_one()
        except Exception:
            with self.connect() as connection:
                self.table.create(bind=connection)
                value = connection.execute(
                    sqlalchemy.text(
                        f"insert into {self.enum_table} (description) values "
                        f"('{i.value}') returning value"
                    )
                ).scalar_one()
            self.load()

        self.cache[self.enum_table].value[Item.Metadata.Enumerable(i.value)] = value
        return value

    def __invert__(self) -> "String":
        return String(
            connect=self.connect, enum_table=self.enum_table, cache_id=self.cache_id
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class String(EnumsTransform, Transforms.Trusted[int, Item.Metadata.Enumerable]):
    def transform(self, i: int) -> Item.Metadata.Enumerable:
        for _ in range(2):
            try:
                return self.cache[self.enum_table].description[i]
            except KeyError:
                self.load()

        raise ValueError(
            f"No description found for enum value `{i}` in table `{self.enum_table}`"
        )

    def __invert__(self) -> Integer:
        return Integer(
            connect=self.connect, enum_table=self.enum_table, cache_id=self.cache_id
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Enum:
    kind: Item.Kind
    kind_transform: Transforms.Safe[Item.Kind, str]

    field: Item.Key
    enum_transform: Transforms.Safe[Item.Key, str]

    connect: Connect
    cache_id: str

    @property
    def db_type(self) -> str:
        return self.kind_transform(self.kind)

    @property
    def db_field(self) -> str:
        return self.enum_transform(self.field)

    @property
    def table(self) -> sqlalchemy.Table:
        return sqlalchemy.Table(
            DbTableName(f"_conveyor_enum_{self.kind.value}")(
                Item.Kind(self.field.value)
            ),
            sqlalchemy.MetaData(),
            *columns(),
        )

    @property
    def column(self) -> sqlalchemy.Column[int]:
        return sqlalchemy.Column(
            self.db_field, sqlalchemy.SmallInteger(), nullable=True
        )

    def index(self, table: sqlalchemy.Table) -> sqlalchemy.Index[int]:
        return sqlalchemy.Index(
            f"index__{self.table.name}", self.db_field, _table=table
        )

    def eq(
        self, description: Item.Metadata.Enumerable
    ) -> sqlalchemy.sql.expression.ColumnElement[bool]:
        return self.column == self.convert(description)

    @typing.overload
    def convert(self, value: Item.Metadata.Enumerable) -> int:
        """"""

    @typing.overload
    def convert(self, value: int | None) -> Item.Metadata.Enumerable:
        """"""

    @dataclasses.dataclass(frozen=True, kw_only=True)
    class Converted:
        source: "Enum"
        value: Item.Metadata.Enumerable | int | None

        def __call__(self):
            return next(iter(self))

        def __iter__(self):
            return itertools.chain(
                self.integer,
                self.enumerable,
                self.none,
            )

        @property
        def integer(self):
            if isinstance(self.value, int):
                yield self.source.string(self.value)

        @property
        def enumerable(self):
            if isinstance(self.value, Item.Metadata.Enumerable):
                match self.value.value:
                    case str():
                        yield self.source.integer(self.value)
                    case None:
                        yield None

        @property
        def none(self):
            if self.value is None:
                yield Item.Metadata.Enumerable(None)

    def convert(
        self, value: Item.Metadata.Enumerable | int | None
    ) -> int | Item.Metadata.Enumerable | None:
        return self.Converted(source=self, value=value)()

    @property
    def integer(self) -> Integer:
        return Integer(
            connect=self.connect, enum_table=self.table.name, cache_id=self.cache_id
        )

    @property
    def string(self) -> String:
        return String(
            connect=self.connect, enum_table=self.table.name, cache_id=self.cache_id
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class Enums:
    connect: Connect
    cache_id: str

    kind_transform: Transforms.Safe[Item.Kind, str]
    enum_transform: Transforms.Safe[Item.Key, str]

    def __getitem__(self, table_and_field: tuple[Item.Kind, Item.Key]):
        return Enum(
            connect=self.connect,
            cache_id=self.cache_id,
            kind=table_and_field[0],
            kind_transform=self.kind_transform,
            field=table_and_field[1],
            enum_transform=self.enum_transform,
        )
