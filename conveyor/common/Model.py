import sys
import typing
import peewee
import datetime
import pydantic
import functools
import playhouse.migrate
import playhouse.reflection

from ..core import Item



MetadataField = peewee.CharField | peewee.IntegerField | peewee.FloatField | peewee.DateTimeField

metadata_fields: dict[type[Item.Metadata.Value], typing.Callable[[], MetadataField]] = {
	str:               functools.partial(peewee.CharField,     index=True, default=None, null=True),
	int:               functools.partial(peewee.IntegerField,  index=True, default=None, null=True),
	float:             functools.partial(peewee.FloatField,    index=True, default=None, null=True),
	datetime.datetime: functools.partial(peewee.DateTimeField, index=True, default=None, null=True)
}


class BaseModel(peewee.Model):
	status   = peewee.CharField(max_length=63, index=True),
	digest   = peewee.CharField(max_length=127, index=True),
	chain    = peewee.CharField(max_length=63, index=True),
	created  = peewee.DateTimeField(index=True, null=False),
	reserver = peewee.CharField(max_length=63, index=True, default=None, null=True)


@pydantic.validate_arguments(config={'arbitrary_types_allowed': True})
def composeMigrator(db: peewee.Database) -> playhouse.migrate.SchemaMigrator:

	if db.__class__ == peewee.SqliteDatabase:
		migrator_class = playhouse.migrate.SqliteMigrator
	elif db.__class__ == peewee.PostgresqlDatabase:
		migrator_class = playhouse.migrate.PostgresqlMigrator
	else:
		raise NotImplementedError(f'No migrator class for db class "{db.__class__}"')

	return migrator_class(db)


models_cache: dict[Item.Type, type[BaseModel]] = {}


@pydantic.validate_arguments(config={'arbitrary_types_allowed': True})
def Model(
	db: peewee.Database,
	name: Item.Type,
	metadata_columns: dict[Item.Metadata.Key, MetadataField] | None=None
) -> type[BaseModel]:

		name = Item.Type(name.value.lower())

		if not metadata_columns:

			if name in models_cache:
				return models_cache[name]

			models: dict[str, type[BaseModel]] = playhouse.reflection.generate_models(db, table_names=[name])
			if len(models):
				models_cache[name] = models[name.value]
				return models[name.value]

			raise KeyError(f"No table with name '{name}' found")

		else:

			Result = type(
				name.value,
				(BaseModel,),
				{
					k: v
					for k, v in BaseModel.__dict__.items()
					if not k.startswith('_') and k not in ['DoesNotExist']
				} | {
					'status'   : peewee.CharField(max_length=63, index=True),
					'digest'   : peewee.CharField(max_length=127, index=True),
					'chain'    : peewee.CharField(max_length=63, index=True),
					'created'  : peewee.DateTimeField(index=True, null=False),
					'reserver' : peewee.CharField(max_length=63, index=True, default=None, null=True),
					'Meta': type(
						'Meta',
						(),
						{
							'database': db
						}
					)
				} | {
					k.value: v
					for k, v in metadata_columns.items()
				}
			)

			if not Result.table_exists():

				with db.transaction():
					try:
						db.create_tables([Result])
					except Exception:
						pass

			else:

				current_columns = [
					c.name
					for c in db.get_columns(name.value)
				]

				migrator = composeMigrator(db)

				with db.atomic():
					playhouse.migrate.migrate(*[
						# migrator.drop_column(name, column_name)
						# for column_name in current_columns
						# if (column_name != 'id') and (column_name not in metadata_columns)
					],*[
						migrator.add_column(name.value, column_name.value, metadata_columns[column_name])
						for column_name in metadata_columns
						if column_name.value not in current_columns
					])

			models_cache[name] = Result

			return Result
