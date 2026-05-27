"""Shared MPG calculation helpers.

These functions are used by the dashboard, fill-up history, and analytics
pages. Keeping the algorithm in one place ensures all three views agree on
what "fleet MPG" or "per-fill-up MPG" means.
"""

from typing import Iterable, Optional


def compute_mpg_data(vehicles):
    """Walk every (prev, curr) fill-up pair across all vehicles.

    Returns:
        prev_odo_map: dict mapping {fill_up.id: previous_odometer_reading}
        fleet_miles:  int — total miles driven across the fleet
        fleet_gallons: float — total gallons used across the fleet

    Vehicles must have ``fill_ups`` eagerly loaded (e.g. via
    ``selectinload(Vehicle.fill_ups)``); no extra queries are issued.
    """
    prev_odo_map = {}
    fleet_miles  = 0
    fleet_gallons = 0.0

    for v in vehicles:
        fps = sorted(v.fill_ups, key=lambda f: (f.date, f.odometer_reading))
        for i in range(1, len(fps)):
            miles = fps[i].odometer_reading - fps[i - 1].odometer_reading
            if miles > 0:
                prev_odo_map[fps[i].id] = fps[i - 1].odometer_reading
                fleet_miles   += miles
                fleet_gallons += fps[i].gallons_pumped

    return prev_odo_map, fleet_miles, fleet_gallons


def fleet_avg_mpg(fleet_miles: int, fleet_gallons: float) -> Optional[float]:
    """Return fleet-wide average MPG, or None if there's no usable data."""
    return (fleet_miles / fleet_gallons) if fleet_gallons > 0 else None


def attach_mpg(fillups_with_vehicles: Iterable, prev_odo_map: dict):
    """Augment (fillup, vehicle) tuples with computed MPG.

    Returns a list of (fillup, vehicle, mpg) tuples where ``mpg`` is a float
    when computable, otherwise None.
    """
    result = []
    for fillup, vehicle in fillups_with_vehicles:
        prev_odo = prev_odo_map.get(fillup.id)
        mpg = None
        if prev_odo is not None:
            miles = fillup.odometer_reading - prev_odo
            if miles > 0 and fillup.gallons_pumped > 0:
                mpg = miles / fillup.gallons_pumped
        result.append((fillup, vehicle, mpg))
    return result
