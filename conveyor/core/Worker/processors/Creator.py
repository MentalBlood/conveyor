import abc
import typing
import dataclasses

from ...Item import Item

from .. import Action
from ..Processor import Processor


@dataclasses.dataclass(frozen=True, kw_only=True)
class Creator(Processor[Item, Action.Action], abc.ABC):
    @abc.abstractmethod
    def process(self, config: typing.Any) -> typing.Iterable[Item]:
        """"""

    @typing.final
    def __call__(
        self, payload: typing.Callable[[], typing.Iterable[Item]], config: typing.Any
    ) -> typing.Iterable[Action.Action]:
        for o in self.process(config):
            yield Action.Append(o)
