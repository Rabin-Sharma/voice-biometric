from datetime import datetime
from app.models import db


class LoginAttempt(db.Model):
    __tablename__ = "login_attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    success = db.Column(db.Boolean, default=False)
    similarity_score = db.Column(db.Float)
    ip_address = db.Column(db.String(64))
    challenge_code = db.Column(db.String(12))
    attempt_time = db.Column(db.DateTime, default=datetime.utcnow)
