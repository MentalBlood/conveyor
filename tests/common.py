from peewee import SqliteDatabase
from playhouse.sqliteq import SqliteQueueDatabase

from conveyor.repositories import Treegres



db = SqliteDatabase(':memory:')
dir_tree_root_path = 'dir_tree'
repository = Treegres(db=db, dir_tree_root_path=dir_tree_root_path)