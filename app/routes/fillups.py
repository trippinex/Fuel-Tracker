from datetime import date
from urllib.parse import urlparse

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload

from ..models import Vehicle, FillUp
from ..database import db
from .analytics import cache as analytics_cache

fillups_bp = Blueprint('fillups', __name__)


def is_safe_redirect(url: str) -> bool:
    """Return True only if *url* is a same-origin relative or absolute path."""
    if not url:
        return False
    parsed = urlparse(url)
    # Relative URLs (no netloc) are safe.
    if not parsed.netloc:
        return True
    # Absolute URLs are safe only when the host matches the current request.
    return parsed.netloc == request.host


@fillups_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_fillup():
    vehicles = Vehicle.query.filter_by(user_id=current_user.id).order_by(Vehicle.name).all()

    if request.method == 'POST':
        vehicle_id_str = request.form.get('vehicle_id', '').strip()
        date_str = request.form.get('date', '').strip()
        odometer_str = request.form.get('odometer_reading', '').strip()
        gallons_str = request.form.get('gallons_pumped', '').strip()
        price_str = request.form.get('price_per_gallon', '').strip()

        errors = []
        vehicle_id = None
        fill_date = None
        odometer = None
        gallons = None
        price = None

        try:
            vehicle_id = int(vehicle_id_str)
            vehicle = db.session.get(Vehicle, vehicle_id)
            if not vehicle or vehicle.user_id != current_user.id:
                errors.append('Selected vehicle does not exist.')
                vehicle_id = None
        except (ValueError, TypeError):
            errors.append('Please select a valid vehicle.')

        try:
            fill_date = date.fromisoformat(date_str)
        except ValueError:
            errors.append('Date must be a valid date (YYYY-MM-DD).')

        try:
            odometer = int(odometer_str)
            if odometer < 0:
                errors.append('Odometer reading must be a positive number.')
        except ValueError:
            errors.append('Odometer reading must be a whole number.')

        try:
            gallons = float(gallons_str)
            if gallons <= 0:
                errors.append('Gallons pumped must be greater than 0.')
        except ValueError:
            errors.append('Gallons pumped must be a valid number.')

        if price_str:
            try:
                price = float(price_str)
                if price < 0:
                    errors.append('Price per gallon cannot be negative.')
            except ValueError:
                errors.append('Price per gallon must be a valid number.')
        else:
            price = 0.0

        if not errors and vehicle_id and odometer is not None:
            latest = (
                FillUp.query
                .filter_by(vehicle_id=vehicle_id)
                .order_by(FillUp.odometer_reading.desc())
                .first()
            )
            if latest and odometer <= latest.odometer_reading:
                errors.append(
                    f'Odometer reading ({odometer:,}) must be greater than the most '
                    f'recent recorded reading ({latest.odometer_reading:,}).'
                )

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('fillup.html', vehicles=vehicles, form_data=request.form)

        fillup = FillUp(
            vehicle_id=vehicle_id,
            date=fill_date,
            odometer_reading=odometer,
            gallons_pumped=gallons,
            price_per_gallon=price,
        )
        db.session.add(fillup)
        db.session.commit()
        analytics_cache.delete(f'analytics_{vehicle_id}')
        flash('Fill-up recorded successfully!', 'success')
        return redirect(url_for('fillups.add_fillup'))

    preselect = request.args.get('vehicle_id')
    return render_template('fillup.html', vehicles=vehicles, form_data={'vehicle_id': preselect})


@fillups_bp.route('/history')
@login_required
def history():
    vehicles = (Vehicle.query
                .filter_by(user_id=current_user.id)
                .options(selectinload(Vehicle.fill_ups))
                .all())

    # Build previous-odometer map for MPG calculation
    prev_odo_map = {}
    for v in vehicles:
        fps = sorted(v.fill_ups, key=lambda f: (f.date, f.odometer_reading))
        for i in range(1, len(fps)):
            miles = fps[i].odometer_reading - fps[i - 1].odometer_reading
            if miles > 0:
                prev_odo_map[fps[i].id] = fps[i - 1].odometer_reading

    _HISTORY_LIMIT = 500
    raw_fillups = (
        db.session.query(FillUp, Vehicle)
        .join(Vehicle, FillUp.vehicle_id == Vehicle.id)
        .filter(Vehicle.user_id == current_user.id)
        .order_by(FillUp.date.desc(), FillUp.id.desc())
        .limit(_HISTORY_LIMIT + 1)   # fetch one extra to detect truncation
        .all()
    )

    truncated = len(raw_fillups) > _HISTORY_LIMIT
    if truncated:
        raw_fillups = raw_fillups[:_HISTORY_LIMIT]

    fillups_with_mpg = []
    for fillup, vehicle in raw_fillups:
        prev_odo = prev_odo_map.get(fillup.id)
        mpg = None
        if prev_odo is not None:
            miles = fillup.odometer_reading - prev_odo
            if miles > 0 and fillup.gallons_pumped > 0:
                mpg = miles / fillup.gallons_pumped
        fillups_with_mpg.append((fillup, vehicle, mpg))

    return render_template('fillups_history.html',
                           fillups=fillups_with_mpg,
                           truncated=truncated,
                           history_limit=_HISTORY_LIMIT)


@fillups_bp.route('/<int:fillup_id>/edit', methods=['POST'])
@login_required
def edit_fillup(fillup_id):
    fillup = db.session.get(FillUp, fillup_id)
    if not fillup or fillup.vehicle.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Fill-up not found.'}), 404

    data   = request.get_json(silent=True) or {}
    errors = []

    # ── Date ─────────────────────────────────────────────────────────────────
    try:
        fill_date = date.fromisoformat(str(data.get('date', '')))
    except (ValueError, TypeError):
        errors.append('Date must be a valid date.')
        fill_date = None

    # ── Odometer ─────────────────────────────────────────────────────────────
    try:
        odometer = int(data.get('odometer_reading', ''))
        if odometer < 0:
            errors.append('Odometer must be a positive number.')
    except (ValueError, TypeError):
        errors.append('Odometer must be a whole number.')
        odometer = None

    # ── Gallons ───────────────────────────────────────────────────────────────
    try:
        gallons = float(data.get('gallons_pumped', ''))
        if gallons <= 0:
            errors.append('Gallons must be greater than 0.')
    except (ValueError, TypeError):
        errors.append('Gallons must be a valid number.')
        gallons = None

    # ── Price (optional) ──────────────────────────────────────────────────────
    price_raw = data.get('price_per_gallon', '')
    if price_raw == '' or price_raw is None:
        price = 0.0
    else:
        try:
            price = float(price_raw)
            if price < 0:
                errors.append('Price cannot be negative.')
        except (ValueError, TypeError):
            errors.append('Price must be a valid number.')
            price = None

    if errors:
        return jsonify({'success': False, 'error': ' '.join(errors)}), 422

    # ── Commit ────────────────────────────────────────────────────────────────
    fillup.date             = fill_date
    fillup.odometer_reading = odometer
    fillup.gallons_pumped   = gallons
    fillup.price_per_gallon = price
    db.session.commit()
    analytics_cache.delete(f'analytics_{fillup.vehicle_id}')

    # ── Recalculate MPG for this fill-up ──────────────────────────────────────
    all_fps = sorted(
        FillUp.query.filter_by(vehicle_id=fillup.vehicle_id).all(),
        key=lambda f: (f.date, f.odometer_reading),
    )
    mpg = None
    for i, f in enumerate(all_fps):
        if f.id == fillup_id and i > 0:
            miles = f.odometer_reading - all_fps[i - 1].odometer_reading
            if miles > 0 and gallons > 0:
                mpg = miles / gallons
            break

    total_cost = gallons * price

    return jsonify({
        'success': True,
        'fillup': {
            'id':               fillup.id,
            'date':             fill_date.isoformat(),
            'date_display':     fill_date.strftime('%b %d, %Y'),
            'odometer_reading': odometer,
            'odometer_display': f'{odometer:,}',
            'gallons_pumped':   gallons,
            'gallons_display':  f'{gallons:.3f}',
            'price_per_gallon': price,
            'price_display':    f'${price:.3f}' if price > 0 else '—',
            'total_cost':       total_cost,
            'total_display':    f'${total_cost:.2f}' if price > 0 else '—',
            'mpg':              round(mpg, 1) if mpg is not None else None,
            'mpg_display':      f'{mpg:.1f}' if mpg is not None else '—',
        },
    })


@fillups_bp.route('/<int:fillup_id>/delete', methods=['POST'])
@login_required
def delete_fillup(fillup_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    fillup  = db.session.get(FillUp, fillup_id)
    if not fillup or fillup.vehicle.user_id != current_user.id:
        if is_ajax:
            return jsonify({'success': False, 'error': 'Fill-up not found.'}), 404
        flash('Fill-up record not found.', 'error')
        return redirect(url_for('main.index'))
    vehicle_id_for_cache = fillup.vehicle_id
    db.session.delete(fillup)
    db.session.commit()
    analytics_cache.delete(f'analytics_{vehicle_id_for_cache}')
    if is_ajax:
        return jsonify({'success': True})
    flash('Fill-up record deleted.', 'success')
    referrer = request.referrer
    return redirect(referrer if is_safe_redirect(referrer) else url_for('main.index'))
