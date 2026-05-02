# Voice Biometric Bank Login System

Convert the existing CLI-based voice biometric system into a web-based(styling with tailwind) **trusted bank login** where users authenticate using **only their voice** — no username, no password, no manual input at all.

## Background

The existing `main.py` uses MFCC features + cosine similarity with a fixed passphrase. This plan upgrades it to:
- **Resemblyzer** deep speaker embeddings (256-dim, language-independent, trained on speaker identity)
- **1:N identification** — voice alone identifies the user from all enrolled accounts
- **Web-based UI** with browser microphone recording
- **Anti-replay liveness detection** — random challenge numbers displayed on each login attempt
- **Premium bank dashboard** showing balances and transactions

---

## User Review Required

> [!IMPORTANT]
> **Database**: The plan uses MySQL (same as your existing `main.py` config: `root:root@localhost:3306/voice_biometric_db`). Confirm this is correct or provide alternative credentials.

> [!IMPORTANT]
> **Resemblyzer vs SpeechBrain**: Resemblyzer is lightweight (~50MB model, CPU-friendly, pip install). SpeechBrain's ECAPA-TDNN is more accurate but heavier (~300MB+ model, PyTorch dependency). **I recommend Resemblyzer** for a hackathon — simpler, fast, and still very good for speaker verification. Confirm or let me know if you prefer SpeechBrain.

> [!WARNING]
> **Browser Microphone Access**: Requires HTTPS in production. For local development, `http://localhost` works fine. Chrome and Firefox both support the Web Audio API / MediaRecorder needed for voice capture.

## Open Questions

1. **Demo bank data**: Should I seed the database with realistic demo account balances and transaction history for registered users, or start with empty accounts?
2. **Account features**: Beyond viewing balance, do you want fund transfer simulation, transaction history, or keep it simple (balance + recent transactions)?
3. **Enrollment samples**: The current system uses 3 samples. Should I keep 3 or increase to 5 for better accuracy?

---

## Proposed Changes

### Folder Structure

```
hackathon/
├── app/
│   ├── __init__.py                 # Flask app factory
│   ├── config.py                   # All configuration
│   ├── models/
│   │   ├── __init__.py             # SQLAlchemy Base + db init
│   │   ├── user.py                 # User model (name, email, voiceprint path)
│   │   ├── account.py              # Bank account model (balance, account_number)
│   │   ├── transaction.py          # Transaction history model
│   │   └── login_attempt.py        # Login attempt audit log
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── auth_controller.py      # Register + voice login logic
│   │   └── dashboard_controller.py # Dashboard / account views
│   ├── services/
│   │   ├── __init__.py
│   │   ├── voice_service.py        # Resemblyzer embedding + matching
│   │   └── account_service.py      # Balance, transactions
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth_routes.py          # /api/register, /api/login, /api/challenge
│   │   └── dashboard_routes.py     # /api/account, /api/transactions
│   ├── migrations/
│   │   └── create_tables.py        # DB schema creation + seeding
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css           # Premium dark banking theme
│   │   └── js/
│   │       ├── recorder.js         # Web Audio API microphone handler
│   │       ├── auth.js             # Login/register UI flow
│   │       └── dashboard.js        # Dashboard interactivity
│   └── templates/
│       ├── base.html               # Base layout (nav, fonts, common CSS/JS)
│       ├── index.html              # Landing / home page
│       ├── register.html           # Multi-step registration wizard
│       ├── login.html              # Voice-only login page
│       └── dashboard.html          # Bank account dashboard
├── voiceprints/                    # Stored .pkl embedding files
├── audio_samples/                  # Temporary WAV uploads (cleaned after processing)
├── requirements.txt
├── run.py                          # App entry point
└── main.py                         # Original CLI version (preserved)
```

---

### Core Services

#### [NEW] [voice_service.py](file:///media/rabin/MyData/experiments/hackathon/app/services/voice_service.py)

The heart of the system. Replaces MFCC with **Resemblyzer** deep speaker embeddings:

- `extract_embedding(audio_path)` → 256-dim numpy vector using `VoiceEncoder.embed_utterance()`
- `enroll_user(user_id, audio_paths)` → Records 3 embeddings, stores mean + individual vectors as `.pkl`
- `identify_speaker(audio_path)` → **1:N search** across ALL enrolled voiceprints, returns best match + score
- `verify_speaker(user_id, audio_path)` → **1:1 verification** against specific user's voiceprint
- Threshold: **0.85** cosine similarity (tunable) — Resemblyzer embeddings are more discriminative than raw MFCC
- **Anti-spoofing**: Liveness challenge — server generates random 4-digit number, user must speak it. We verify the spoken number via speech recognition before accepting the voice sample. This prevents replay attacks.

#### [NEW] [account_service.py](file:///media/rabin/MyData/experiments/hackathon/app/services/account_service.py)

- `create_account(user_id)` → Creates bank account with random account number and seeded balance
- `get_balance(user_id)` → Returns current balance
- `get_transactions(user_id)` → Returns transaction history
- `seed_transactions(account_id)` → Generates realistic demo transaction data

---

### Database Models

#### [NEW] [user.py](file:///media/rabin/MyData/experiments/hackathon/app/models/user.py)

```python
class User:
    id              # Primary key
    full_name       # User's display name
    email           # Unique email
    voiceprint_path # Path to .pkl file
    is_locked       # Account lock after failed attempts
    failed_attempts # Counter
    created_at      # Timestamp
```

#### [NEW] [account.py](file:///media/rabin/MyData/experiments/hackathon/app/models/account.py)

```python
class Account:
    id              # Primary key
    user_id         # FK to User
    account_number  # Random 10-digit bank account number
    balance         # Decimal balance
    account_type    # "savings" / "checking"
    created_at      # Timestamp
```

#### [NEW] [transaction.py](file:///media/rabin/MyData/experiments/hackathon/app/models/transaction.py)

```python
class Transaction:
    id              # Primary key
    account_id      # FK to Account
    type            # "credit" / "debit"
    amount          # Decimal
    description     # e.g., "Salary Deposit", "ATM Withdrawal"
    balance_after   # Running balance
    created_at      # Timestamp
```

#### [NEW] [login_attempt.py](file:///media/rabin/MyData/experiments/hackathon/app/models/login_attempt.py)

```python
class LoginAttempt:
    id              # Primary key
    user_id         # FK (nullable — may not match)
    success         # Boolean
    similarity_score # Float
    ip_address      # Client IP
    challenge_code  # The random number shown
    attempt_time    # Timestamp
```

---

### API Routes

#### [NEW] [auth_routes.py](file:///media/rabin/MyData/experiments/hackathon/app/routes/auth_routes.py)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Landing page |
| `GET` | `/register` | Registration page |
| `GET` | `/login` | Voice login page |
| `POST` | `/api/register` | Submit registration (name, email + 3 voice samples) |
| `GET` | `/api/challenge` | Get random 4-digit liveness challenge number |
| `POST` | `/api/login` | Submit voice sample → 1:N identification → return JWT-like session |
| `POST` | `/api/logout` | Clear session |

#### [NEW] [dashboard_routes.py](file:///media/rabin/MyData/experiments/hackathon/app/routes/dashboard_routes.py)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/dashboard` | Bank dashboard page (requires auth) |
| `GET` | `/api/account` | Get account details + balance |
| `GET` | `/api/transactions` | Get recent transactions |

---

### Frontend Pages

#### [NEW] Landing Page (`index.html`)
- Hero section with bank branding ("VoiceVault Bank")
- Animated voice waveform background
- Two CTA buttons: "Open Account" and "Voice Login"
- Premium dark theme with gold accents

#### [NEW] Registration Page (`register.html`)
- **Step 1**: Enter full name and email (only manual input in entire app)
- **Step 2**: Record 3 voice samples (speak anything — "say any sentence in any language")
- **Step 3**: Success confirmation with account details
- Live waveform visualizer during recording
- Progress indicator for enrollment steps

#### [NEW] Login Page (`login.html`)
- **No input fields at all** — just a microphone button
- Shows random 4-digit challenge number: "Please say this number: **7 2 9 4**"
- User clicks mic → speaks the number → system identifies them by voice
- Animated recording indicator with pulsing rings
- Real-time feedback: "Listening...", "Processing...", "Welcome back, [Name]!"

#### [NEW] Dashboard Page (`dashboard.html`)
- User greeting with name
- Account balance card with large formatted number
- Account details (account number, type, member since)
- Recent transactions table with credit/debit color coding
- "Voice Logout" or standard logout button

---

### Frontend JavaScript

#### [NEW] [recorder.js](file:///media/rabin/MyData/experiments/hackathon/app/static/js/recorder.js)
- Uses `navigator.mediaDevices.getUserMedia()` for microphone access
- `MediaRecorder` API to capture audio as WAV
- Real-time waveform visualization using `AnalyserNode`
- Auto-stop after configurable duration (3 seconds)
- Returns audio blob for upload to server

#### [NEW] [auth.js](file:///media/rabin/MyData/experiments/hackathon/app/static/js/auth.js)
- Registration wizard step management
- Multi-sample enrollment flow (record → upload → next)
- Login flow: fetch challenge → record → upload → handle result
- Session management via cookies

#### [NEW] [dashboard.js](file:///media/rabin/MyData/experiments/hackathon/app/static/js/dashboard.js)
- Fetch and render account data
- Transaction list with animations
- Balance display with count-up animation

---

### Security & Robustness

1. **Language Independence**: Resemblyzer extracts speaker identity features (vocal tract shape, pitch, timbre) — NOT speech content. Same speaker saying different things in different languages produces similar embeddings.

2. **Anti-Replay (Liveness)**: Each login attempt shows a fresh random 4-digit number. The user must speak it. We verify:
   - The **spoken content** matches the challenge (via speech recognition)
   - The **voice identity** matches an enrolled user (via Resemblyzer embedding)
   
   This means a recording of someone's voice won't work — they'd need to say the correct random number.

3. **Anti-Impersonation**: Even if someone says the same passphrase with a similar-sounding voice, the 256-dimensional speaker embedding captures fine-grained vocal characteristics that are extremely hard to mimic. Threshold of 0.85 provides strong discrimination.

4. **Account Locking**: After 5 failed attempts, account is locked (requires admin reset).

5. **Audit Trail**: Every login attempt is logged with similarity score, IP, and challenge code.

---

## Verification Plan

### Automated Tests
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run database migrations
python -m app.migrations.create_tables

# 3. Start the server
python run.py

# 4. Browser testing via browser tool:
#    - Navigate to http://localhost:5000
#    - Register a new user with voice samples
#    - Login using voice only
#    - Verify dashboard shows account balance
```

### Manual Verification
- Register a user → verify voiceprint file created in `voiceprints/`
- Login with same voice → verify access granted
- Try login with different person → verify access denied
- Verify liveness: replay a recorded audio → should fail (wrong challenge number)
- Check database has proper user, account, transaction, and login attempt records
