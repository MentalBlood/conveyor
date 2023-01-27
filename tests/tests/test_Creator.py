import pytest
import typing
import pydantic

from conveyor.core import Worker
from conveyor.core.Worker import processors
from conveyor.core import Mask, Query, Repository

from ..common import *



@pytest.fixture
@pydantic.validate_arguments
def receiver(item: Item) -> Worker.Receiver:
	return Worker.Receiver((
		lambda _: Mask(
			type = item.type
		),
	))


@pytest.fixture
def creator() -> processors.Creator:

	class C(processors.Creator):
		def process(self, config: dict[str, typing.Any]) -> typing.Iterable[Item]:
			for i in config['items']:
				match i:
					case Item():
						yield i
					case _:
						pass

	return C()


@pytest.fixture
@pydantic.validate_arguments
def worker(receiver: Worker.Receiver, creator: processors.Creator, repository: Repository) -> Worker.Worker:
	return Worker.Worker(
		receiver   = receiver,
		processor  = creator,
		repository = repository
	)


@pydantic.validate_arguments
def test_creator_create_one_item(worker: Worker.Worker, item: Item, query_all: Query):
	for _ in range(2):
		worker({'items': (item,)})
		for i in worker.repository[query_all]:
			assert i == item