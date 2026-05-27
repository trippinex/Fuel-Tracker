from flask import Blueprint, render_template, request, jsonify
from flask_caching import Cache
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload

from ..models import Vehicle, FillUp
from ..database import db
from ..services.ownership import get_owned_vehicle

analytics_bp = Blueprint('analytics', __name__)

# Module-level cache instance; initialized against the app in app/__init__.py.
cache = Cache(config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})


def _compute_analytics(vehicle: Vehicle) -> dict:
    cache_key = f'analytics_{vehicle.id}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    fill_ups = (
        FillUp.query
        .filter_by(vehicle_id=vehicle.id)
        .order_by(FillUp.date, FillUp.odometer_reading)
        .all()
    )

    count = len(fill_ups)
    if count == 0:
        result = {'vehicle': vehicle, 'fill_ups_count': 0, 'has_data': False, 'fillup_records': []}
        cache.set(cache_key, result)
        return result

    fillup_records = [
        {
            'date': f.date.isoformat(),
            'odometer': f.odometer_reading,
            'gallons': f.gallons_pumped,
            'price': f.price_per_gallon,
        }
        for f in fill_ups
    ]

    total_gallons = sum(f.gallons_pumped for f in fill_ups)
    total_spend = sum(f.gallons_pumped * f.price_per_gallon for f in fill_ups)

    mpg_values = []
    distances = []
    day_diffs = []
    chart_dates = []
    chart_mpg = []
    chart_gallons = []
    chart_cost = []

    for i, fillup in enumerate(fill_ups):
        if i == 0:
            chart_dates.append(fillup.date.strftime('%Y-%m-%d'))
            chart_gallons.append(round(fillup.gallons_pumped, 3))
            chart_cost.append(round(fillup.gallons_pumped * fillup.price_per_gallon, 2))
            chart_mpg.append(None)
            continue

        prev = fill_ups[i - 1]
        distance = fillup.odometer_reading - prev.odometer_reading
        day_diff = (fillup.date - prev.date).days

        chart_dates.append(fillup.date.strftime('%Y-%m-%d'))
        chart_gallons.append(round(fillup.gallons_pumped, 3))
        chart_cost.append(round(fillup.gallons_pumped * fillup.price_per_gallon, 2))

        if day_diff >= 0:
            day_diffs.append(day_diff)

        if distance > 0 and fillup.gallons_pumped > 0:
            mpg = distance / fillup.gallons_pumped
            mpg_values.append(mpg)
            distances.append(distance)
            chart_mpg.append(round(mpg, 2))
        else:
            chart_mpg.append(None)

    total_miles = (fill_ups[-1].odometer_reading - fill_ups[0].odometer_reading) if count > 1 else 0

    avg_mpg = sum(mpg_values) / len(mpg_values) if mpg_values else None
    best_mpg = max(mpg_values) if mpg_values else None
    worst_mpg = min(mpg_values) if mpg_values else None
    avg_distance = sum(distances) / len(distances) if distances else None
    avg_days = sum(day_diffs) / len(day_diffs) if day_diffs else None
    cost_per_mile = total_spend / total_miles if total_miles > 0 else None
    estimated_range = vehicle.fuel_capacity_gallons * avg_mpg if avg_mpg else None

    result = {
        'vehicle': vehicle,
        'fill_ups_count': count,
        'has_data': True,
        'fillup_records': fillup_records,
        'avg_mpg': round(avg_mpg, 2) if avg_mpg is not None else None,
        'best_mpg': round(best_mpg, 2) if best_mpg is not None else None,
        'worst_mpg': round(worst_mpg, 2) if worst_mpg is not None else None,
        'total_gallons': round(total_gallons, 3),
        'total_miles': total_miles,
        'cost_per_mile': round(cost_per_mile, 4) if cost_per_mile is not None else None,
        'total_spend': round(total_spend, 2),
        'avg_distance': round(avg_distance, 1) if avg_distance is not None else None,
        'estimated_range': round(estimated_range, 1) if estimated_range is not None else None,
        'avg_days': round(avg_days, 1) if avg_days is not None else None,
        'chart_dates': chart_dates,
        'chart_mpg': chart_mpg,
        'chart_gallons': chart_gallons,
        'chart_cost': chart_cost,
    }
    cache.set(cache_key, result)
    return result


@analytics_bp.route('/')
@login_required
def analytics():
    vehicles = (Vehicle.query
                .filter_by(user_id=current_user.id)
                .options(selectinload(Vehicle.fill_ups))
                .order_by(Vehicle.name)
                .all())
    if not vehicles:
        return render_template('analytics.html', vehicles=[], stats=None, selected_vehicle=None)

    vehicle_id_str = request.args.get('vehicle_id')
    selected_vehicle = None

    if vehicle_id_str:
        try:
            selected_vehicle = get_owned_vehicle(int(vehicle_id_str))
        except (ValueError, TypeError):
            pass

    if selected_vehicle is None:
        selected_vehicle = vehicles[0]

    stats = _compute_analytics(selected_vehicle)

    return render_template('analytics.html',
                           vehicles=vehicles,
                           stats=stats,
                           selected_vehicle=selected_vehicle)


@analytics_bp.route('/data/<int:vehicle_id>')
@login_required
def analytics_data(vehicle_id):
    vehicle = get_owned_vehicle(vehicle_id)
    if not vehicle:
        return jsonify({'error': 'Vehicle not found'}), 404
    stats = _compute_analytics(vehicle)
    stats.pop('vehicle', None)
    return jsonify(stats)
