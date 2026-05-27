"""Authorization helper — ensures the current user owns the requested vehicle.

Centralising this check guards against accidentally exposing another user's
vehicle through a new endpoint.
"""

from flask_login import current_user

from ..database import db
from ..models import Vehicle


def get_owned_vehicle(vehicle_id):
    """Return the Vehicle if it exists AND belongs to current_user, else None.

    The caller decides how to handle the None case — flash + redirect,
    JSON 404, abort, etc.
    """
    vehicle = db.session.get(Vehicle, vehicle_id)
    if not vehicle or vehicle.user_id != current_user.id:
        return None
    return vehicle
