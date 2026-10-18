from frappe.model.document import Document
from plus_point.events import validate_vehicle_booking


class PPVehicleBooking(Document):
    def validate(self):
        validate_vehicle_booking(self)
