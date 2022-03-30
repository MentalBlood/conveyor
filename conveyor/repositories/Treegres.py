import os
import lzma
import base64
import growing_tree_base
from blake3 import blake3
from typing import Callable
from functools import lru_cache, partial
from dataclasses import dataclass, asdict, replace
from peewee import Field, CharField, IntegerField, FloatField, Database, Model as Model_

from .. import Item, Repository, Model



class Path(str):
	def __new__(C, value):
		return super().__new__(
			C,
			os.path.normpath(os.path.normcase(value))
		)


ignored_fields = [
	'id',
	'type',
	'data',
	'metadata'
]

def getFields(item: Item) -> dict[str, None | str | int | float | Path]:
	return {
		k: None if v == '' else v
		for k, v in (item.metadata | asdict(item)).items()
		if k not in ignored_fields
	}


base_fields_mapping: dict[str, Callable[[], Field]] = {
	'chain_id': partial(CharField, max_length=63, index=True),
	'status': partial(CharField, max_length=63, index=True),
	'data_digest': partial(CharField, max_length=63)
}

metadata_fields_mapping: dict[type, Callable[[], Field]] = {
	str: partial(CharField, default=None, null=True, index=True),
	int: partial(IntegerField, default=None, null=True, index=True),
	float: partial(FloatField, default=None, null=True, index=True),
	Path: partial(CharField, max_length=63, index=True)
}

def getModel(db: Model_, item: Item) -> Model_:
	return Model(
		db=db,
		name=item.type,
		columns={
			k: base_fields_mapping[k]()
			for k in asdict(item)
			if k not in ignored_fields
		} | {
			k: metadata_fields_mapping[type(v)]()
			for k, v in item.metadata.items()
		}
	)


def getDigest(data: bytes) -> str:
	d = blake3(data, max_threads=blake3.AUTO).digest()
	return base64.b64encode(d).decode('ascii')


@dataclass
class File:

	path: str

	def set(self, content: bytes):
		with lzma.open(self.path, 'wb', filters=[
			{"id": lzma.FILTER_LZMA2, "preset": lzma.PRESET_EXTREME},
		]) as f:
			f.write(content)

	def get(self, digest):

		if not hasattr(self, 'content'):

			with lzma.open(self.path, 'rb') as f:
				file_bytes = f.read()

			self.content = file_bytes.decode()
			self.correct_digest = getDigest(file_bytes)

		if self.correct_digest != digest:
			raise Exception(f"Cannot get file content: digest invalid: '{digest}' != '{self.correct_digest}'")

		return self.content


def getFile(path):
	return File(path)


@dataclass
class Treegres(Repository):

	db: Database
	dir_tree_root_path: str

	cache_size: int = 1024

	def __post_init__(self):
		self.getFile = lru_cache(maxsize=self.cache_size)(getFile)

	def create(self, item):

		item_data_bytes = item.data.encode('utf8')
		item.data_digest = getDigest(item_data_bytes)
		type_dir_path = os.path.join(self.dir_tree_root_path, item.type)

		file_absolute_path = growing_tree_base.Tree(
			root=type_dir_path,
			base_file_name='.xz',
			save_file_function=lambda p, c: getFile(p).set(c)
		).save(item_data_bytes)

		result_item = replace(
			item,
			data_digest=getDigest(item_data_bytes),
			metadata=(
				item.metadata
				| {'file_path': Path(os.path.relpath(file_absolute_path, type_dir_path))}
			)
		)

		return getModel(self.db, result_item)(**getFields(result_item)).save()

	def fetch(self, type, status, limit=None):

		model = Model(self.db, type)
		if not model:
			return []

		query_result = model.select().where(model.status==status).limit(limit)
		result = []

		for r in query_result:

			r_dict = {
				k: v if v.__class__ == str else v
				for k, v in r.__data__.items()
			}

			file_path = Path(os.path.join(self.dir_tree_root_path, type, r_dict['file_path']))

			item = Item(
				type=type,
				status=status,
				id=r_dict['id'],
				chain_id=r_dict['chain_id'],
				data_digest = r_dict['data_digest'],
				data=self.getFile(file_path).get(r_dict['data_digest'])
			)
			item.metadata = {
				k: v
				for k, v in r_dict.items()
				if not k in [*asdict(item).keys()]
			}

			result.append(item)
		
		return result
	
	def get(self, type, where=None, fields=None, limit=1):

		model = Model(self.db, type)
		if not model:
			return []
		
		if fields == None:
			get_fields = []
		else:
			get_fields = [
				getattr(model, f)
				for f in fields
				if hasattr(model, f)
			]

		conditions = [
			getattr(model, key)==value
			for key, value in where.items()
		]
		query_result = model.select(*get_fields).where(*conditions).limit(limit)

		result = []

		for r in query_result:

			if fields == None:

				file_path = Path(os.path.join(self.dir_tree_root_path, type, r.file_path))

				item = Item(
					type=type,
					status=r.status,
					id=r.id,
					chain_id=r.chain_id,
					data_digest = r.data_digest,
					data=self.getFile(file_path).get(r.data_digest)
				)
				item.metadata = {
					k: v
					for k, v in r.__data__.items()
					if not k in asdict(item).keys()
				}

			else:

				item = Item(type=type, **{
					name: getattr(r, name)
					for name in fields
					if hasattr(r, name)
				})

				if 'data' in fields:
					file_path = Path(os.path.join(self.dir_tree_root_path, type, r.file_path))
					item.data=self.getFile(file_path).get(r.data_digest)
				
				if 'metadata' in fields:
					item.metadata = {
						k: v
						for k, v in r.__data__.items()
						if not k in asdict(item).keys()
					}
		
			result.append(item)

		return result

	def update(self, type, id, item):

		model = Model(self.db, type)
		if not model:
			return None

		return model.update(**getFields(item)).where(model.id==id).execute()

	def delete(self, type, id):

		model = Model(self.db, type)
		if not model:
			return None

		file_path = Path(model.select().where(model.id==id).get().__data__['file_path'])

		result = model.delete().where(model.id==id).execute()

		try:
			os.remove(file_path)
		except FileNotFoundError:
			pass
		
		return result

	@property
	def transaction(self):

		def decorator(f):
			def new_f(*args, **kwargs):
				with self.db.transaction():
					result = f(*args, **kwargs)
				return result
			return new_f

		return decorator
	
	def _drop(self, type: str) -> int:

		model = Model(self.db, type)
		if not model:
			return None
		
		return self.db.drop_tables([model])
