import json
import logging
import re
from datetime import datetime, date as date_cls

logger = logging.getLogger(__name__)

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, Response)
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload

from ..models import Vehicle, FillUp
from ..database import db

settings_bp = Blueprint('settings', __name__)

# ── Settings page ─────────────────────────────────────────────────────────────

@settings_bp.route('/settings')
@login_required
def settings():
    return render_template('settings.html')


# ── Export ────────────────────────────────────────────────────────────────────

@settings_bp.route('/settings/export')
@login_required
def export_backup():
    vehicles = (Vehicle.query
                .filter_by(user_id=current_user.id)
                .options(selectinload(Vehicle.fill_ups))
                .order_by(Vehicle.name)
                .all())

    payload = {
        'app': 'FuelTrack',
        'version': 1,
        'exported_at': datetime.utcnow().isoformat(),
        'vehicles': [],
    }

    for v in vehicles:
        fps = sorted(v.fill_ups, key=lambda f: (f.date, f.odometer_reading))
        payload['vehicles'].append({
            'name': v.name,
            'make': v.make,
            'model': v.model,
            'year': v.year,
            'fuel_capacity_gallons': v.fuel_capacity_gallons,
            'vin': v.vin,
            'license_plate': v.license_plate,
            'fill_ups': [
                {
                    'date': f.date.isoformat(),
                    'odometer_reading': f.odometer_reading,
                    'gallons_pumped': f.gallons_pumped,
                    'price_per_gallon': f.price_per_gallon,
                }
                for f in fps
            ],
        })

    body = json.dumps(payload, separators=(',', ':')).encode('utf-8')

    # Use the browser-supplied local timestamp if present and well-formed,
    # otherwise fall back to the server's UTC datetime.
    ts = request.args.get('ts', '').strip()
    if not re.match(r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}$', ts):
        ts = datetime.utcnow().strftime('%Y-%m-%d_%H-%M')
    filename = f'fueltrack-backup-{ts}.json'

    return Response(
        body,
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Length': len(body),
        },
    )


# ── Import ────────────────────────────────────────────────────────────────────

_REQUIRED_VEHICLE = {'name', 'make', 'model', 'year', 'fuel_capacity_gallons'}
_REQUIRED_FILLUP  = {'date', 'odometer_reading', 'gallons_pumped'}


_MAX_VEHICLES       = 500
_MAX_FILLUPS_PER_VH = 5_000


def _validate(data):
    """Return an error string, or None if the payload looks valid."""
    if not isinstance(data, dict):
        return 'File is not a JSON object.'
    if data.get('app') != 'FuelTrack':
        return 'Not a FuelTrack backup (missing or wrong "app" key).'
    if not isinstance(data.get('vehicles'), list):
        return 'Missing "vehicles" array.'

    if len(data['vehicles']) > _MAX_VEHICLES:
        return f'Backup contains too many vehicles (max {_MAX_VEHICLES}).'

    for i, v in enumerate(data['vehicles'], 1):
        missing = _REQUIRED_VEHICLE - set(v.keys())
        if missing:
            return f'Vehicle #{i} ("{v.get("name", "?")}") is missing: {", ".join(sorted(missing))}.'
        fill_ups = v.get('fill_ups', [])
        if len(fill_ups) > _MAX_FILLUPS_PER_VH:
            return (f'Vehicle "{v.get("name", "?")}" has too many fill-ups '
                    f'(max {_MAX_FILLUPS_PER_VH:,} per vehicle).')
        for j, f in enumerate(fill_ups, 1):
            missing_f = _REQUIRED_FILLUP - set(f.keys())
            if missing_f:
                return (f'Fill-up #{j} for vehicle "{v["name"]}" '
                        f'is missing: {", ".join(sorted(missing_f))}.')
    return None


@settings_bp.route('/settings/import', methods=['POST'])
@login_required
def import_backup():
    file = request.files.get('backup_file')

    if not file or not file.filename:
        flash('No file selected.', 'error')
        return redirect(url_for('settings.settings'))

    if not file.filename.lower().endswith('.json'):
        flash('Invalid file type — please upload a .json backup file.', 'error')
        return redirect(url_for('settings.settings'))

    # Read (cap at 5 MB — a backup should never be larger)
    try:
        raw  = file.read(5 * 1024 * 1024)
        data = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        flash('Could not parse the file. Make sure it is a valid FuelTrack backup.', 'error')
        return redirect(url_for('settings.settings'))

    err = _validate(data)
    if err:
        flash(f'Invalid backup file: {err}', 'error')
        return redirect(url_for('settings.settings'))

    # ── Replace existing data ─────────────────────────────────────────────────
    try:
        # Cascade-delete all fill-ups then vehicles for this user
        for v in Vehicle.query.filter_by(user_id=current_user.id).all():
            for f in v.fill_ups:
                db.session.delete(f)
            db.session.delete(v)
        db.session.flush()

        # Re-insert from backup
        total_fillups = 0
        for vd in data['vehicles']:
            vehicle = Vehicle(
                user_id=current_user.id,
                name=str(vd['name']),
                make=str(vd['make']),
                model=str(vd['model']),
                year=int(vd['year']),
                fuel_capacity_gallons=float(vd['fuel_capacity_gallons']),
                vin=vd.get('vin') or None,
                license_plate=vd.get('license_plate') or None,
                # photo_filename intentionally omitted — photos not in backup
            )
            db.session.add(vehicle)
            db.session.flush()  # populate vehicle.id

            for fd in vd.get('fill_ups', []):
                db.session.add(FillUp(
                    vehicle_id=vehicle.id,
                    date=date_cls.fromisoformat(fd['date']),
                    odometer_reading=int(fd['odometer_reading']),
                    gallons_pumped=float(fd['gallons_pumped']),
                    price_per_gallon=float(fd.get('price_per_gallon', 0.0)),
                ))
                total_fillups += 1

        db.session.commit()

        v_count = len(data['vehicles'])
        flash(
            f'Backup restored — '
            f'{v_count} vehicle{"s" if v_count != 1 else ""} and '
            f'{total_fillups} fill-up{"s" if total_fillups != 1 else ""} imported.',
            'success',
        )

    except Exception as exc:
        db.session.rollback()
        logger.exception('Backup restore failed for user %s', current_user.id)
        flash('Restore failed due to an unexpected error. Please try again or contact support.', 'error')
        return redirect(url_for('settings.settings'))

    return redirect(url_for('main.index'))
