import imghdr
import os

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, abort, current_app
from flask_login import login_required, current_user

from ..models import Vehicle
from ..database import db

ALLOWED_PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}

vehicles_bp = Blueprint('vehicles', __name__)


@vehicles_bp.route('/')
@login_required
def list_vehicles():
    vehicles = Vehicle.query.filter_by(user_id=current_user.id).order_by(Vehicle.year.desc(), Vehicle.name).all()
    return render_template('vehicles.html', vehicles=vehicles)


@vehicles_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        make = request.form.get('make', '').strip()
        model = request.form.get('model', '').strip()
        year_str = request.form.get('year', '').strip()
        capacity_str = request.form.get('fuel_capacity_gallons', '').strip()
        vin = request.form.get('vin', '').strip().upper() or None
        license_plate = request.form.get('license_plate', '').strip().upper() or None

        errors = []
        if not name:
            errors.append('Vehicle name is required.')
        if not make:
            errors.append('Make is required.')
        if not model:
            errors.append('Model is required.')
        try:
            year = int(year_str)
            if year < 1900 or year > 2100:
                errors.append('Year must be between 1900 and 2100.')
        except ValueError:
            errors.append('Year must be a valid integer.')
            year = None
        try:
            capacity = float(capacity_str)
            if capacity <= 0:
                errors.append('Fuel capacity must be greater than 0.')
        except ValueError:
            errors.append('Fuel capacity must be a valid number.')
            capacity = None

        # Validate photo if provided
        photo_file = request.files.get('photo')
        photo_ext = None
        if photo_file and photo_file.filename:
            # 1. Size cap (5 MB)
            photo_file.seek(0, 2)
            photo_size = photo_file.tell()
            photo_file.seek(0)
            if photo_size > 5 * 1024 * 1024:
                errors.append('Photo must be smaller than 5 MB.')
            else:
                # 2. Extension check
                photo_ext = os.path.splitext(photo_file.filename)[1].lower()
                if photo_ext not in ALLOWED_PHOTO_EXTENSIONS:
                    errors.append('Photo must be a JPG, PNG, or WebP image.')
                    photo_ext = None
                else:
                    # 3. MIME check (imghdr reads magic bytes, not the filename)
                    header = photo_file.read(512)
                    photo_file.seek(0)
                    detected = imghdr.what(None, h=header)
                    if detected not in ('jpeg', 'png', 'webp'):
                        errors.append('Photo content does not match a supported image type.')
                        photo_ext = None

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('add_vehicle.html', form_data=request.form)

        vehicle = Vehicle(
            user_id=current_user.id,
            name=name,
            make=make,
            model=model,
            year=year,
            fuel_capacity_gallons=capacity,
            vin=vin,
            license_plate=license_plate,
        )
        db.session.add(vehicle)
        db.session.commit()

        # Save photo now that we have the vehicle ID
        if photo_ext:
            photos_dir = current_app.config['PHOTOS_PATH']
            filename = f'vehicle_{vehicle.id}{photo_ext}'
            photo_file.save(os.path.join(photos_dir, filename))
            vehicle.photo_filename = filename
            db.session.commit()

        flash(f'Vehicle "{name}" added successfully!', 'success')
        return redirect(url_for('vehicles.list_vehicles'))

    return render_template('add_vehicle.html', form_data={})


@vehicles_bp.route('/<int:vehicle_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_vehicle(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id)
    if not vehicle or vehicle.user_id != current_user.id:
        flash('Vehicle not found.', 'error')
        return redirect(url_for('vehicles.list_vehicles'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        make = request.form.get('make', '').strip()
        model = request.form.get('model', '').strip()
        year_str = request.form.get('year', '').strip()
        capacity_str = request.form.get('fuel_capacity_gallons', '').strip()
        vin = request.form.get('vin', '').strip().upper() or None
        license_plate = request.form.get('license_plate', '').strip().upper() or None
        remove_photo = request.form.get('remove_photo', '')
        errors = []
        photo_file = request.files.get('photo')
        photo_ext = None
        if photo_file and photo_file.filename:
            # 1. Size cap (5 MB)
            photo_file.seek(0, 2)
            photo_size = photo_file.tell()
            photo_file.seek(0)
            if photo_size > 5 * 1024 * 1024:
                errors.append('Photo must be smaller than 5 MB.')
            else:
                # 2. Extension check
                photo_ext = os.path.splitext(photo_file.filename)[1].lower()
                if photo_ext not in ALLOWED_PHOTO_EXTENSIONS:
                    errors.append('Photo must be a JPG, PNG, or WebP image.')
                    photo_ext = None
                else:
                    # 3. MIME check
                    header = photo_file.read(512)
                    photo_file.seek(0)
                    detected = imghdr.what(None, h=header)
                    if detected not in ('jpeg', 'png', 'webp'):
                        errors.append('Photo content does not match a supported image type.')
                        photo_ext = None
        if not name:
            errors.append('Vehicle name is required.')
        if not make:
            errors.append('Make is required.')
        if not model:
            errors.append('Model is required.')
        try:
            year = int(year_str)
            if year < 1900 or year > 2100:
                errors.append('Year must be between 1900 and 2100.')
        except ValueError:
            errors.append('Year must be a valid integer.')
            year = None
        try:
            capacity = float(capacity_str)
            if capacity <= 0:
                errors.append('Fuel capacity must be greater than 0.')
        except ValueError:
            errors.append('Fuel capacity must be a valid number.')
            capacity = None

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('edit_vehicle.html', vehicle=vehicle, form_data=request.form)

        vehicle.name = name
        vehicle.make = make
        vehicle.model = model
        vehicle.year = year
        vehicle.fuel_capacity_gallons = capacity
        vehicle.vin = vin
        vehicle.license_plate = license_plate

        # Handle photo changes
        photos_dir = current_app.config['PHOTOS_PATH']
        if (remove_photo or photo_ext) and vehicle.photo_filename:
            old_path = os.path.join(photos_dir, vehicle.photo_filename)
            if os.path.exists(old_path):
                os.remove(old_path)
            vehicle.photo_filename = None
        if photo_ext:
            filename = f'vehicle_{vehicle.id}{photo_ext}'
            photo_file.save(os.path.join(photos_dir, filename))
            vehicle.photo_filename = filename

        db.session.commit()
        flash(f'Vehicle "{name}" updated successfully!', 'success')
        return redirect(url_for('vehicles.list_vehicles'))

    return render_template('edit_vehicle.html', vehicle=vehicle, form_data={
        'name': vehicle.name,
        'make': vehicle.make,
        'model': vehicle.model,
        'year': vehicle.year,
        'fuel_capacity_gallons': vehicle.fuel_capacity_gallons,
        'vin': vehicle.vin or '',
        'license_plate': vehicle.license_plate or '',
    })


@vehicles_bp.route('/photo/<path:filename>')
@login_required
def vehicle_photo(filename):
    # Ownership check: only serve the photo if it belongs to the current user.
    # Use vehicle.photo_filename from the DB (not the raw user-supplied filename)
    # to prevent path-traversal via crafted filenames.
    vehicle = Vehicle.query.filter_by(
        photo_filename=filename,
        user_id=current_user.id,
    ).first()
    if not vehicle:
        abort(404)
    return send_from_directory(current_app.config['PHOTOS_PATH'], vehicle.photo_filename)


@vehicles_bp.route('/<int:vehicle_id>/photo', methods=['POST'])
@login_required
def upload_photo(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id)
    if not vehicle or vehicle.user_id != current_user.id:
        flash('Vehicle not found.', 'error')
        return redirect(url_for('vehicles.list_vehicles'))

    file = request.files.get('photo')
    if not file or file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('vehicles.list_vehicles'))

    # 1. Size cap (5 MB)
    file.seek(0, 2)
    if file.tell() > 5 * 1024 * 1024:
        flash('Photo must be smaller than 5 MB.', 'error')
        return redirect(url_for('vehicles.list_vehicles'))
    file.seek(0)

    # 2. Extension check
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_PHOTO_EXTENSIONS:
        flash('Please upload a JPG, PNG, or WebP image.', 'error')
        return redirect(url_for('vehicles.list_vehicles'))

    # 3. MIME check
    header = file.read(512)
    file.seek(0)
    if imghdr.what(None, h=header) not in ('jpeg', 'png', 'webp'):
        flash('Photo content does not match a supported image type.', 'error')
        return redirect(url_for('vehicles.list_vehicles'))

    photos_dir = current_app.config['PHOTOS_PATH']

    # Remove old photo if it exists
    if vehicle.photo_filename:
        old_path = os.path.join(photos_dir, vehicle.photo_filename)
        if os.path.exists(old_path):
            os.remove(old_path)

    filename = f'vehicle_{vehicle_id}{ext}'
    file.save(os.path.join(photos_dir, filename))
    vehicle.photo_filename = filename
    db.session.commit()
    flash('Photo updated.', 'success')
    return redirect(url_for('vehicles.list_vehicles'))


@vehicles_bp.route('/<int:vehicle_id>/photo/delete', methods=['POST'])
@login_required
def delete_photo(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id)
    if not vehicle or vehicle.user_id != current_user.id:
        flash('Vehicle not found.', 'error')
        return redirect(url_for('vehicles.list_vehicles'))

    if vehicle.photo_filename:
        path = os.path.join(current_app.config['PHOTOS_PATH'], vehicle.photo_filename)
        if os.path.exists(path):
            os.remove(path)
        vehicle.photo_filename = None
        db.session.commit()
        flash('Photo removed.', 'success')

    return redirect(url_for('vehicles.list_vehicles'))


@vehicles_bp.route('/<int:vehicle_id>/delete', methods=['POST'])
@login_required
def delete_vehicle(vehicle_id):
    vehicle = db.session.get(Vehicle, vehicle_id)
    if not vehicle or vehicle.user_id != current_user.id:
        flash('Vehicle not found.', 'error')
        return redirect(url_for('vehicles.list_vehicles'))
    name = vehicle.name
    db.session.delete(vehicle)
    db.session.commit()
    flash(f'Vehicle "{name}" and all its fill-up records have been deleted.', 'success')
    return redirect(url_for('vehicles.list_vehicles'))
