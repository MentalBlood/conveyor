from ..core import Worker



class Destroyer(Worker):

	input_type: str
	input_status: str

	receive_fields = ['id']

	def processItem(self, item):
		return self.repository.delete(item.type, item.id)