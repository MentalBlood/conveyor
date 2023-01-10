import typing
import shutil
import pathlib
import pydantic
import contextlib
import dataclasses

from .Transaction import Transaction
from ...core.Item import Digest, Data
from .Transforms import Transform, Transforms



@pydantic.dataclasses.dataclass(frozen=True, kw_only=True)
class Core:

	Transform  = Transform
	Transforms = Transforms

	root: pathlib.Path
	suffix: pydantic.StrictStr
	granulation: pydantic.PositiveInt

	transform:  Transform[bytes]
	equal:      Transform[bytes]

	transaction_: Transaction | None = None

	@classmethod
	@pydantic.validate_arguments
	def _segment(cls, s: str) -> str:
		match s:
			case '+':
				return 'plus'
			case '/':
				return 'slash'
			case '=':
				return 'equal'
			case _:
				return s

	@classmethod
	@pydantic.validate_arguments
	def _group(cls, l: typing.Iterable[str], size: int) -> typing.Iterable[str]:

		buffer = ''

		for e in l:
			if len(e) == 1:
				buffer += e
				if len(buffer) == size:
					yield buffer
					buffer = ''
			else:
				yield e

	@pydantic.validate_arguments
	def path(self, digest: Digest) -> pathlib.Path:
		return pathlib.Path(
			self.root,
			pathlib.Path(
			*Core._group(
				map(
					Core._segment,
					digest.string
				),
				self.granulation
			)
		)
	).with_suffix(self.suffix)

	@pydantic.validate_arguments
	def append(self, data: Data) -> None:
		with self.transaction() as t:
			if t.transaction_ is not None:
				t.transaction_.append(
					Transaction.Append(
						path  = self.path(data.digest),
						data  = self.transform(data.value),
						equal_path = lambda b: self.path(Data(value = b).digest),
						equal_data = self.equal
					)
				)
			else:
				raise ValueError

	@pydantic.validate_arguments
	def __getitem__(self, digest: Digest) -> Data:
		try:
			return Data(
				value = (~self.transform)(
					self.path(digest).read_bytes()
				),
				test = digest
			)
		except FileNotFoundError:
			raise KeyError(f'{self.root} {digest.string}')
		except ValueError:
			raise

	@pydantic.validate_arguments
	def __delitem__(self, digest: Digest) -> None:
		with self.transaction() as t:
			if t.transaction_ is not None:
				t.transaction_.append(Transaction.Delete(self.path(digest)))
			else:
				raise ValueError

	@contextlib.contextmanager
	def transaction(self) -> typing.Iterator[typing.Self]:

		if self.transaction_ is None:
			t = dataclasses.replace(
				self,
				transaction_ = Transaction()
			)
		else:
			t = self

		if t.transaction_ is None:
			raise ValueError

		try:
			yield t
			if self.transaction_ is None:
				t.transaction_.commit()
		except:
			t.transaction_.rollback()
			raise

	@pydantic.validate_arguments
	def __contains__(self, digest: Digest) -> bool:
		return self.path(digest).exists()

	def __len__(self) -> pydantic.NonNegativeInt:

		result: pydantic.NonNegativeInt = 0

		for _ in self.root.rglob(f'*{self.suffix}'):
			result += 1

		return result

	def clear(self) -> None:
		shutil.rmtree(self.root, ignore_errors=True)