# VoiceVault Bank Login (Hackathon)

VoiceVault is a Flask web app for voice biometric login.

## Features

- 1:N speaker identification using SpeechBrain ECAPA embeddings.
- Enrollment with 5 voice samples.
- User-defined key sentence (passphrase) stored at registration.
- Strict passphrase verification at login:
  - recognized speech must exactly match the passphrase after normalization.
  - no fuzzy/substring acceptance.
- Voice-only login screen (no username/password input).
- Bank dashboard with account details and recent transactions.
- Account locking feature flag (disabled by default).

## Tech Stack

- Python 3.12
- Flask + Flask-SQLAlchemy
- MySQL + PyMySQL
- SpeechBrain + Torch + Torchaudio
- Browser MediaRecorder + Web Audio API
- Tailwind CSS (CDN)

## Project Structure

- `app/` Flask app modules, routes, services, templates, static assets
- `audio_samples/` uploaded enrollment/login wav files
- `voiceprints/` serialized speaker embeddings
- `main.py` original CLI prototype
- `run.py` Flask entrypoint

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create database:

```bash
mysql -u root -proot -e "CREATE DATABASE IF NOT EXISTS voice_biometric_db;"
```

Create tables:

```bash
./venv/bin/python3 -m app.migrations.create_tables
```

Run server:

```bash
./venv/bin/python3 run.py
```

Open:

- `http://127.0.0.1:5000`

## Usage Flow

1. Open **Register**.
2. Enter full name, email, and your key sentence.
3. Record 5 samples by repeating the same key sentence exactly.
4. Open **Voice Login** and say the same key sentence.
5. If speaker + passphrase match, you enter dashboard.

## Important Notes

- `ENABLE_ACCOUNT_LOCKING` is `False` by default in `app/config.py`.
- Passphrase matching is strict after normalization (lowercase, punctuation/extra spaces removed).
- If login fails, frontend shows debug details (`heard` transcript and similarity `score`).

## Troubleshooting

- `Table ... doesn't exist`:
  - run migrations again.
- `Unknown database voice_biometric_db`:
  - create DB first.
- `speechbrain.inference` import errors:
  - this project uses `speechbrain.pretrained` path.
- flaky recognition:
  - use quiet room and same microphone for enrollment/login.
