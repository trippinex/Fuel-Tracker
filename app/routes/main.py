from datetime import date as date_cls

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload

from ..models import Vehicle, FillUp
from ..database import db
from ..services.mpg import compute_mpg_data, fleet_avg_mpg, attach_mpg

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
        .limit(5)
        .all()
    )

    # ── Aggregate stats computed in Python from already-loaded fill_ups ──
    # Saves three round-trips to the database vs. issuing COUNT/SUM queries.
    total_vehicles = len(vehicles)
    total_fillups  = 0
    total_spend    = 0.0
    total_gallons  = 0.0
    for v in vehicles:
        for f in v.fill_ups:
            total_fillups += 1
            total_spend   += f.gallons_pumped * f.price_per_gallon
            total_gallons += f.gallons_pumped

    # ── Vehicle with the most recent fill-up (for mobile dashboard) ─────────
    most_recent_vehicle_id = None
    _latest_date = None
    for v in vehicles:
        if v.fill_ups:
            v_latest = max(v.fill_ups, key=lambda f: (f.date, f.id))
            if _latest_date is None or v_latest.date > _latest_date:
                _latest_date = v_latest.date
                most_recent_vehicle_id = v.id

    # ── Fleet avg MPG + per-fill-up MPG map (shared helper) ─────────────────
    prev_odo_map, fleet_miles, fleet_gallons = compute_mpg_data(vehicles)
    avg_mpg = fleet_avg_mpg(fleet_miles, fleet_gallons)

    # Attach MPG to each recent fill-up
    recent_with_mpg = attach_mpg(recent_fillups, prev_odo_map)

    # ── Key insight ───────────────────────────────────────────────────────────
    insight = None
    if avg_mpg is not None:
        insight = f"Fleet average {avg_mpg:.1f} MPG across {total_fillups} fill-up{'s' if total_fillups != 1 else ''}"
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
        fleet_avg_mpg=avg_mpg,
        insight=insight,
        first_name=first_name,
    )
