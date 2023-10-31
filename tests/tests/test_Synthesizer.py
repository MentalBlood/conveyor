import pytest
import typing
import dataclasses

from conveyor.core import Worker, Item
from conveyor.core.Worker import processors
from conveyor.core import Mask, Query, Repository

from ..common import *


@pytest.fixture
def synthesizer() -> processors.Synthesizer:
    class M(processors.Synthesizer):
        def process(
            self, input: Item, matched: typing.Iterable[Item]
        ) -> typing.Iterable[Item.Status | Item]:
            print("PROCESS")

            yield Item.Status(f"{input.status.value}_")

            for m in matched:
                yield dataclasses.replace(
                    m,
                    type=Item.Type("new"),
                    status=Item.Status("created"),
                    metadata=m.metadata,
                )
                break

    return M()


@pytest.fixture
def worker(
    synthesizer: processors.Synthesizer, repository: Repository
) -> Worker.Worker:
    return Worker.Worker(
        receiver=Worker.Receiver(
            masks=(
                lambda _: Mask(type=Item.Type("type")),
                lambda items: Mask(
                    type=Item.Type("another"),
                    metadata=Item.Metadata(
                        {Item.Metadata.Key("id"): items[-1].metadata["id"]}
                    ),
                ),
            ),
            limit=None,
        ),
        processor=synthesizer,
        repository=repository,
    )


def test_synthesizer(worker: Worker.Worker, item: Item):
    worker.repository.append(
        dataclasses.replace(
            item,
            type=Item.Type("type"),
            metadata=Item.Metadata({Item.Metadata.Key("id"): "123"}),
        )
    )
    worker.repository.append(
        dataclasses.replace(
            item,
            type=Item.Type("another"),
            metadata=Item.Metadata(
                {Item.Metadata.Key("id"): "123", Item.Metadata.Key("color"): "red"}
            ),
        )
    )

    worker()

    assert len(worker.repository) == 3
    for i in worker.repository[Query(mask=Mask(type=Item.Type("new")), limit=None)]:
        assert i.metadata == Item.Metadata(
            {Item.Metadata.Key("id"): "123", Item.Metadata.Key("color"): "red"}
        )
