import re
import typing
import datetime
import pydantic
import frozendict

from .Data import Data
from .Created import Created



@pydantic.dataclasses.dataclass(frozen=True, kw_only=False)
class Word:

	value: pydantic.StrictStr

	@pydantic.validator('value')
	def value_correct(cls, value):
		if re.match(r'\w+', value) is None:
			raise ValueError('`Word` value must be word')
		return value


@pydantic.dataclasses.dataclass(frozen=True, kw_only=True)
class Item:

	@pydantic.dataclasses.dataclass(frozen=True, kw_only=False)
	class Metadata:

		Value = pydantic.StrictStr | int | float | datetime.datetime

		value: dict[Word, Value]

		@pydantic.validator('value')
		def value_correct(cls, value):
			return frozendict.frozendict(value)

	Type          = Word
	Status        = Word
	Reserved      = str | None

	BaseValue     = typing.Union[Type, Status, 'Chain', Created, Reserved]
	Value         = BaseValue | Metadata.Value

	type:           Type
	status:         Status

	data:           Data

	metadata:       Metadata

	chain:          'Chain'
	created:        Created
	reserved:       Reserved



from .Chain import Chain
Item.__pydantic_model__.update_forward_refs()