import abc
import typing
import dataclasses

from ...Item import Item

from .. import Action
from ..Processor import Processor


@dataclasses.dataclass(frozen=True, kw_only=True)
class Transformer(Processor[Item, Action.Action], abc.ABC):
    @abc.abstractmethod
    def process(self, payload: Item) -> typing.Iterable[Item.Status | Item.Metadata]:
        """"""

    def _process(self, i: Item):
        try:
            for o in self.process(i):
                match o:
                    case Item.Status():
                        yield Action.Update(old=i, new=dataclasses.replace(i, status=o))
                    case Item.Metadata():
                        yield Action.Update(
                            old=i,
                            new=dataclasses.replace(i, metadata=i.metadata | o),
                        )
        except Exception as e:
            raise self.error(i, e) from e

        yield Action.Success(i)

    @typing.final
    def __call__(
        self,
        payload: typing.Callable[[], typing.Iterable[Item]],
        config: typing.Any = None,
    ) -> typing.Iterable[Action.Action]:
        for i in payload():
            yield from self._process(i)
            break
