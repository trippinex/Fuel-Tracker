from datetime import date as date_cls

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload

from ..models import Vehicle, FillUp
from ..database import db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    uid = current_user.id

    vehicles = (Vehicle.query
                .filter_by(user_id=uid)
                .options(selectinload(Vehicle.fill_ups))
                .order_by(Vehicle.name)
                .all())

    recent_fillups = (
        db.session.query(FillUp, Vehicle)
        .join(Vehicle, FillUp.vehicle_id == Vehicle.id)
        .filter(Vehicle.user_id == uid)
        .order_by(FillUp.date.desc(), FillUp.id.desc())
        .limit(10)
        .all()
    )

    total_vehicles = len(vehicles)

    total_fillups = (
        db.session.query(db.func.count(FillUp.id))
        .join(Vehicle, FillUp.vehicle_id == Vehicle.id)
        .filter(Vehicle.user_id == uid)
        .scalar()
    ) or 0

    total_spend = (
        db.session.query(db.func.sum(FillUp.gallons_pumped * FillUp.price_per_gallon))
        .join(Vehicle, FillUp.vehicle_id == Vehicle.id)
        .filter(Vehicle.user_id == uid)
        .scalar()
    ) or 0.0

    total_gallons = (
        db.session.query(db.func.sum(FillUp.gallons_pumped))
        .join(Vehicle, FillUp.vehicle_id == Vehicle.id)
        .filter(Vehicle.user_id == uid)
        .scalar()
    ) or 0.0

    # ── Vehicle with the most recent fill-up (for mobile dashboard) ─────────
    most_recent_vehicle_id = None
    _latest_date = None
    for v in vehicles:
        if v.fill_ups:
            v_latest = max(v.fill_ups, key=lambda f: (f.date, f.id))
            if _latest_date is None or v_latest.date > _latest_date:
                _latest_date = v_latest.date
                most_recent_vehicle_id = v.id

    # ── Fleet avg MPG + per-fill-up MPG map ──────────────────────────────────
    # For each vehicle build an ordered fill-up list; compute Δmiles / gallons
    # for every fill-up after the first (first has no prior odometer reading).
    prev_odo_map = {}          # fill-up id → previous odometer reading
    fleet_miles   = 0
    fleet_gallons = 0.0

    for v in vehicles:
        fps = sorted(v.fill_ups, key=lambda f: (f.date, f.odometer_reading))
        for i in range(1, len(fps)):
            miles = fps[i].odometer_reading - fps[i - 1].odometer_reading
            if miles > 0:
                prev_odo_map[fps[i].id] = fps[i - 1].odometer_reading
                fleet_miles   += miles
                fleet_gallons += fps[i].gallons_pumped

    fleet_avg_mpg = (fleet_miles / fleet_gallons) if fleet_gallons > 0 else None

    # Attach MPG to each recent fill-up
    recent_with_mpg = []
    for fillup, vehicle in recent_fillups:
        prev_odo = prev_odo_map.get(fillup.id)
        mpg = None
        if prev_odo is not None:
            miles = fillup.odometer_reading - prev_odo
            if miles > 0 and fillup.gallons_pumped > 0:
                mpg = miles / fillup.gallons_pumped
        recent_with_mpg.append((fillup, vehicle, mpg))

    # ── Key insight ───────────────────────────────────────────────────────────
    insight = None
    if fleet_avg_mpg is not None:
        insight = f"Fleet average {fleet_avg_mpg:.1f} MPG across {total_fillups} fill-up{'s' if total_fillups != 1 else ''}"
    elif total_fillups > 0:
        last = (
            db.session.query(FillUp)
            .join(Vehicle, FillUp.vehicle_id == Vehicle.id)
            .filter(Vehicle.user_id == uid)
            .order_by(FillUp.date.desc())
            .first()
        )
        if last:
            days = (date_cls.today() - last.date).days
            insight = f"Last fill-up was {days} day{'s' if days != 1 else ''} ago"

    raw_name = current_user.name or current_user.email
    first_name = raw_name.split()[0] if raw_name else 'there'

    return render_template(
        'index.html',
        vehicles=vehicles,
        most_recent_vehicle_id=most_recent_vehicle_id,
        recent_fillups=recent_with_mpg,
        total_vehicles=total_vehicles,
        total_fillups=total_fillups,
        total_spend=total_spend,
        total_gallons=total_gallons,
        fleet_avg_mpg=fleet_avg_mpg,
        insight=insight,
        first_name=first_name,
    )
