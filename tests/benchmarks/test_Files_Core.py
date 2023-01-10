import pytest
import pathlib

from tests.common import *

from conveyor.core.Item import Data



@pytest.fixture
def empty() -> Data:
	return Data(value = b'')


@pytest.mark.benchmark(group='files')
def test_add_same_empty(benchmark, files: Files.Core, empty: Data):
	benchmark(files.append, empty)
	files.clear()


@pytest.fixture
def big() -> Data:
	return Data(value = (pathlib.Path(__file__).parent / 'test_big_data.td').read_bytes())


@pytest.mark.benchmark(group='files')
def test_add_same_big(benchmark, files: Files.Core, big: Data):
	benchmark(files.append, big)
	files.clear()