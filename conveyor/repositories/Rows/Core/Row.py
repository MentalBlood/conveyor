import typing
import pydantic

from ....core import Item

from .Enums import Enums



@pydantic.dataclasses.dataclass(frozen=True, kw_only=True)
class Row:

	type:     Item.Type
	status:   Item.Status

	digest:   Item.Data.Digest
	metadata: Item.Metadata

	chain:    str
	created:  Item.Created
	reserver: Item.Reserver

	@pydantic.validator('metadata')
	def metadata_valid(cls, metadata: Item.Metadata, values: dict[str, Item.Value | Item.Metadata.Value]) -> Item.Metadata:
		for k in metadata.value:
			if k.value in values:
				raise KeyError(f'Field name "{k.value}" reserved and can not be used in metadata')
		return metadata

	@classmethod
	@pydantic.validate_arguments
	def from_item(cls, item: Item) -> typing.Self:
		return Row(
			type     = item.type,
			status   = item.status,
			digest   = item.data.digest,
			chain    = item.chain.value,
			created  = item.created,
			reserver = item.reserver,
			metadata = item.metadata
		)

	def dict_(self, enums: Enums.Enums, skip: set[str] = set()) -> dict[str, Item.Metadata.Value]:

		result: dict[str, Item.Metadata.Value] = {}

		status = enums[(self.type, Item.Metadata.Key('status'))]
		if status.db_field not in skip:
			result[status.db_field] = status.Int(Item.Metadata.Enumerable(self.status.value))

		if 'chain' not in skip:
			result['chain'] = self.chain
		if 'digest' not in skip:
			result['digest'] = self.digest.string
		if 'created' not in skip:
			result['created'] = self.created.value
		if 'reserver' not in skip:
			result['reserver'] = self.reserver.value

		for key, value in self.metadata.value.items():
			if key.value not in skip:
				match value:
					case Item.Metadata.Enumerable():
						e = enums[(self.type, key)]
						result[e.db_field] = e.Int(value)
					case _:
						result[key.value] = value

		return result

	def sub(self, another: 'Row', enums: Enums.Enums) -> dict[str, Item.Metadata.Value]:

		skip: set[str] = set()

		if self.status == another.status:
			skip.add('status')
		if self.digest == another.digest:
			skip.add('digest')
		if self.chain == another.chain:
			skip.add('chain')
		if self.created == another.created:
			skip.add('created')
		if self.reserver == another.reserver:
			skip.add('reserver')

		skip |= {
			k.value
			for k in self.metadata.value.keys()
			if self.metadata.value[k] == another.metadata.value[k]
		}

		return self.dict_(enums, skip)