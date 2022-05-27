import pydantic
from datetime import datetime
from peewee import Database, CharField, DateTimeField, IntegerField

from ...core import Item
from ...common import Model



class ItemId(int):

	@pydantic.validate_arguments
	def __new__(C, value: str | int):

		if type(value) == int:
			return super().__new__(C, value)

		elif type(value) == str:
			if not len(value):
				result_value = -1
			else:
				result_value = int(value)
			return super().__new__(C, result_value)


class ExceptionLogsRepository:

	@pydantic.validate_arguments(config={'arbitrary_types_allowed': True})
	def __init__(self, db: Database, name: str='conveyor_errors') -> None:

		self.db = db
		self.exceptions = Model(db, name, columns={
			'date': DateTimeField(index=True),
			'worker_name': CharField(max_length=63, index=True),
			'item_type': CharField(max_length=63, null=True, index=True),
			'item_status': CharField(max_length=63, null=True, index=True),
			'item_chain_id': CharField(max_length=63, null=True, index=True),
			'item_id': IntegerField(null=True, index=True),
			'error_type': CharField(max_length=63),
			'error_text': CharField(max_length=255)
		}, uniques=[(
			'worker_name',
			'item_chain_id',
			'item_id',
			'error_type',
			'error_text'
		)])

	@pydantic.validate_arguments
	def create(self, item: Item, exception_type: str, exception_text: str, worker_name: str) -> int:

		return self.exceptions.insert(
			date=str(datetime.utcnow()),
			worker_name=worker_name,
			item_type=item.type,
			item_status=item.status,
			item_chain_id=item.chain_id,
			item_id=ItemId(item.id),
			error_type=exception_type,
			error_text=exception_text[:255]
		).on_conflict('replace').execute()

	# def delete(self, item: Item) -> int:
