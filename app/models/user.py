from datetime import datetime
from app.models import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    passphrase = db.Column(db.String(255), nullable=False)
    voiceprint_path = db.Column(db.String(255))
    is_locked = db.Column(db.Boolean, default=False)
    failed_attempts = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    account = db.relationship("Account", uselist=False, back_populates="user")
