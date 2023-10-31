import abc
import typing
import dataclasses

from ...Item import Item

from .. import Action
from ..Processor import Processor


@dataclasses.dataclass(frozen=True, kw_only=True)
class Synthesizer(Processor[Item, Action.Action], metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def process(
        self, input: Item, matched: typing.Iterable[Item]
    ) -> typing.Iterable[Item.Status | Item]:
        pass

    @typing.final
    def __call__(
        self, input: typing.Callable[[], typing.Iterable[Item]], config: typing.Any = {}
    ) -> typing.Iterable[Action.Action]:
        iterator = iter(input())

        for i in iterator:
            try:
                for o in self.process(i, iter(iterator)):
                    match o:
                        case Item.Status():
                            yield Action.Update(
                                old=i, new=dataclasses.replace(i, status=o)
                            )
                        case Item():
                            if o.chain != i.chain:
                                raise ValueError(
                                    f"Output chain ({o.chain}) must be equal "
                                    f"to input chain ({i.chain})"
                                )
                            yield Action.Append(o)
            except Exception as e:
                raise self.error(i, e)

            yield Action.Success(i)
            break
