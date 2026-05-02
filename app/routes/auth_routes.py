import os
import uuid
from flask import Blueprint, current_app, jsonify, render_template, request, session
from app.models import db
from app.models.user import User
from app.models.login_attempt import LoginAttempt
from app.services.voice_service import VoiceService
from app.services.account_service import AccountService


auth_routes = Blueprint("auth_routes", __name__)


def _save_upload(file_storage, base_dir, prefix):
    os.makedirs(base_dir, exist_ok=True)
    filename = f"{prefix}_{uuid.uuid4().hex}.wav"
    path = os.path.join(base_dir, filename)
    file_storage.save(path)
    return path


def _log_login_attempt(user_id, success, score, challenge_code, ip_address):
    attempt = LoginAttempt(
        user_id=user_id,
        success=success,
        similarity_score=score,
        ip_address=ip_address,
        challenge_code=challenge_code,
    )
    db.session.add(attempt)
    db.session.commit()


@auth_routes.get("/")
def index():
    return render_template("index.html")


@auth_routes.get("/register")
def register_page():
    return render_template("register.html")


@auth_routes.get("/login")
def login_page():
    return render_template("login.html")


@auth_routes.post("/api/register")
def register():
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    passphrase = request.form.get("passphrase", "").strip()
    samples = request.files.getlist("samples")

    if not full_name or not email or not passphrase:
        return jsonify({"error": "Full name, email, and passphrase are required."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered."}), 409

    if len(samples) < current_app.config["ENROLLMENT_SAMPLES"]:
        return jsonify({"error": "Not enough samples."}), 400

    user = User(full_name=full_name, email=email, passphrase=passphrase)
    db.session.add(user)
    db.session.commit()

    audio_dir = os.path.join(current_app.config["AUDIO_DIR"], f"user_{user.id}")
    audio_paths = []
    for sample in samples[: current_app.config["ENROLLMENT_SAMPLES"]]:
        audio_paths.append(_save_upload(sample, audio_dir, "enroll"))

    voice_service = VoiceService(current_app.config)
    try:
        voiceprint_path = voice_service.enroll_user(user.id, audio_paths)
    except Exception as exc:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"error": f"Enrollment failed: {exc}"}), 500

    user.voiceprint_path = voiceprint_path
    db.session.commit()

    AccountService().create_account(user.id)

    return jsonify({"success": True, "user_id": user.id})


@auth_routes.post("/api/login")
def login():
    sample = request.files.get("sample")
    if not sample:
        return jsonify({"error": "No audio provided."}), 400

    temp_dir = os.path.join(current_app.config["AUDIO_DIR"], "temp")
    audio_path = _save_upload(sample, temp_dir, "login")
    lock_enabled = current_app.config.get("ENABLE_ACCOUNT_LOCKING", False)

    voice_service = VoiceService(current_app.config)
    try:
        user_id, score = voice_service.identify_speaker(audio_path)
        if not user_id or score < current_app.config["SPEAKER_THRESHOLD"]:
            user = User.query.get(user_id) if user_id else None
            if lock_enabled and user:
                user.failed_attempts += 1
                if user.failed_attempts >= current_app.config["ACCOUNT_LOCK_THRESHOLD"]:
                    user.is_locked = True
                db.session.commit()
                _log_login_attempt(user.id, False, score, None, request.remote_addr)
            else:
                _log_login_attempt(None, False, score, None, request.remote_addr)
            return jsonify({"error": "Voice not recognized.", "score": score}), 401

        user = User.query.get(user_id)
        if not user:
            _log_login_attempt(None, False, score, None, request.remote_addr)
            return jsonify({"error": "User not found.", "score": score}), 404

        if lock_enabled and (user.is_locked or user.failed_attempts >= current_app.config["ACCOUNT_LOCK_THRESHOLD"]):
            return jsonify({"error": "Account locked.", "score": score}), 403

        passphrase_ok, recognized = voice_service.verify_passphrase(
            audio_path, user.passphrase
        )
        if not passphrase_ok:
            if lock_enabled:
                user.failed_attempts += 1
                if user.failed_attempts >= current_app.config["ACCOUNT_LOCK_THRESHOLD"]:
                    user.is_locked = True
                db.session.commit()
            _log_login_attempt(user.id, False, score, None, request.remote_addr)
            return (
                jsonify({"error": "Passphrase failed.", "heard": recognized, "score": score}),
                401,
            )

        if lock_enabled:
            user.failed_attempts = 0
            db.session.commit()

        _log_login_attempt(user.id, True, score, None, request.remote_addr)
        session["user_id"] = user.id

        return jsonify(
            {"success": True, "user_id": user.id, "full_name": user.full_name, "score": score}
        )
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


@auth_routes.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"success": True})
