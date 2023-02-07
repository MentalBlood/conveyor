import typing
import pydantic
import datetime
import dataclasses

from ... import Item

from .. import Action
from ..Processor import Processor



@pydantic.dataclasses.dataclass(frozen=True, kw_only=True)
class Logger(Processor[Action.Action, Action.Action]):

	normal : Item.Type
	errors : Item.Type

	@pydantic.validate_arguments
	def __call__(self, input: typing.Callable[[], typing.Iterable[Action.Action]], config: dict[str, typing.Any]) -> typing.Iterable[Action.Action]:

		try:

			for a in input():

				match a:

					case Action.Success():
						yield Action.Solution(
							ref  = a,
							type = self.errors
						)

					case _:

						info: dict[Item.Metadata.Key, Item.Metadata.Value] = {}
						for k, v in a.info:
							match v:
								case Item.Metadata.Value:
									info[Item.Metadata.Key(f'action_{k}')] = v
								case Item():
									info[Item.Metadata.Key(f'action_{k}_type')]   = Item.Metadata.Enumerable(v.type.value)
									info[Item.Metadata.Key(f'action_{k}_status')] = Item.Metadata.Enumerable(v.status.value)
								case _ :
									pass

						entry = Item(
							type     = self.normal,
							status   = Item.Status('preaction'),
							data     = Item.Data(value = b''),
							metadata = Item.Metadata(info | {
								Item.Metadata.Key('action') : Item.Metadata.Enumerable(a.__class__.__name__),
							}),
							chain    = Item.Chain(ref = Item.Data(value = str(a).encode())),
							reserver = Item.Reserver(exists = False, value = None),
							created  = Item.Created(datetime.datetime.now())
						)

						yield Action.Append(entry)
						yield a
						yield Action.Update(
							old = entry,
							new = dataclasses.replace(entry, status = Item.Status('postaction'))
						)

		except Processor.Error[Item] as e:

			yield Action.Error(
				old       = e.input,
				exception = e.exception,
				type      = self.errors
			)