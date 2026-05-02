import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    mysql_host = os.environ.get("MYSQL_HOST", "localhost")
    mysql_user = os.environ.get("MYSQL_USER", "root")
    mysql_password = os.environ.get("MYSQL_PASSWORD", "root")
    mysql_db = os.environ.get("MYSQL_DB", "voice_biometric_db")
    mysql_port = os.environ.get("MYSQL_PORT", "3306")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    AUDIO_DIR = str(BASE_DIR / "audio_samples")
    VOICEPRINT_DIR = str(BASE_DIR / "voiceprints")

    SAMPLE_RATE = 16000
    RECORD_DURATION_SEC = 3
    ENROLLMENT_SAMPLES = 5
    SPEAKER_THRESHOLD = 0.75

    CHALLENGE_LENGTH = 4
    ACCOUNT_LOCK_THRESHOLD = 5
    ENABLE_ACCOUNT_LOCKING = False

    SPEECHBRAIN_MODEL = "speechbrain/spkrec-ecapa-voxceleb"
