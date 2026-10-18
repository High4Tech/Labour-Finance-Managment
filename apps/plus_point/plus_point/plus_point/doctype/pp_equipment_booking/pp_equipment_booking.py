from frappe.model.document import Document
from plus_point.events import validate_equipment_booking


class PPEquipmentBooking(Document):
    def validate(self):
        validate_equipment_booking(self)
