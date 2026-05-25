from datetime import datetime

from flask_login import UserMixin

from .database import db


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    name = db.Column(db.String(200))
    picture = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    vehicles = db.relationship('Vehicle', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'


class Vehicle(db.Model):
    __tablename__ = 'vehicles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    fuel_capacity_gallons = db.Column(db.Float, nullable=False)
    vin = db.Column(db.String(17), nullable=True)
    license_plate = db.Column(db.String(20), nullable=True)
    photo_filename = db.Column(db.String(200), nullable=True)

    fill_ups = db.relationship('FillUp', backref='vehicle', lazy=True,
                               cascade='all, delete-orphan',
                               order_by='FillUp.date, FillUp.odometer_reading')

    def __repr__(self):
        return f'<Vehicle {self.name}>'


class FillUp(db.Model):
    __tablename__ = 'fill_ups'

    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicles.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    odometer_reading = db.Column(db.Integer, nullable=False)
    gallons_pumped = db.Column(db.Float, nullable=False)
    price_per_gallon = db.Column(db.Float, nullable=False)

    @property
    def total_cost(self):
        return self.gallons_pumped * self.price_per_gallon

    def __repr__(self):
        return f'<FillUp {self.id} vehicle={self.vehicle_id}>'
