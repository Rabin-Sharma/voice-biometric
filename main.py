#!/usr/bin/env python3
"""
Voice Biometric Login System - Simplified Working Version
"""

import sys
import numpy as np
import librosa
import sounddevice as sd
import pickle
import os
from pathlib import Path
from scipy.spatial.distance import cosine
from datetime import datetime
import speech_recognition as sr
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pymysql

# Configuration
SAMPLE_RATE = 16000
RECORD_DURATION = 3
ENROLLMENT_SAMPLES = 3  # Reduced for faster testing
VERIFICATION_THRESHOLD = 0.75
PASSPHRASE = "the bed is dry"

# Paths
BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "audio_samples"
VOICEPRINT_DIR = BASE_DIR / "voiceprints"

# Create directories
AUDIO_DIR.mkdir(exist_ok=True)
VOICEPRINT_DIR.mkdir(exist_ok=True)

# MySQL Configuration
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'voice_biometric_db',
    'port': 3306
}

# SQLAlchemy setup
DATABASE_URL = f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    email = Column(String(100), unique=True)
    full_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    voiceprint_path = Column(String(255))
    failed_attempts = Column(Integer, default=0)

class LoginAttempt(Base):
    __tablename__ = "login_attempts"
    id = Column(Integer, primary_key=True)
    username = Column(String(50))
    success = Column(Boolean)
    similarity_score = Column(Float)
    attempt_time = Column(DateTime, default=datetime.utcnow)

class VoiceBiometricSystem:
    def __init__(self):
        self.sample_rate = SAMPLE_RATE
        self.duration = RECORD_DURATION
        self.passphrase = PASSPHRASE
        self.threshold = VERIFICATION_THRESHOLD
    
    def record_audio(self, prompt=None):
        if prompt:
            print(f"\n🎤 {prompt}")
        else:
            print(f"\n🎤 Please say: '{self.passphrase}'")
        
        input("Press Enter when ready...")
        
        try:
            print("🔴 Recording...")
            recording = sd.rec(int(self.duration * self.sample_rate), 
                              samplerate=self.sample_rate, 
                              channels=1, 
                              dtype='float32')
            sd.wait()
            print("✅ Done!")
            return recording.flatten()
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def save_audio(self, audio_data, user_id, sample_num=None):
        from scipy.io.wavfile import write
        user_dir = AUDIO_DIR / f"user_{user_id}"
        user_dir.mkdir(exist_ok=True)
        
        if sample_num:
            filename = f"sample_{sample_num}.wav"
        else:
            filename = f"login_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        
        filepath = user_dir / filename
        write(str(filepath), self.sample_rate, (audio_data * 32767).astype(np.int16))
        return str(filepath)
    
    def extract_features(self, audio_path):
        try:
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            mfcc_mean = np.mean(mfcc, axis=1)
            mfcc_std = np.std(mfcc, axis=1)
            features = np.concatenate([mfcc_mean, mfcc_std])
            return features
        except Exception as e:
            print(f"Feature error: {e}")
            return None
    
    def verify_passphrase(self, audio_path):
        try:
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_path) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio).lower()
            print(f"🔍 Recognized: '{text}'")
            return self.passphrase in text or text in self.passphrase
        except:
            return False
    
    def enroll_user(self, user_id, num_samples=ENROLLMENT_SAMPLES):
        print(f"\n{'='*50}")
        print(f"🎙️  Enrolling: {user_id}")
        print(f"{'='*50}")
        
        features_list = []
        
        for i in range(num_samples):
            print(f"\nSample {i+1}/{num_samples}")
            audio_data = self.record_audio()
            
            if audio_data is None:
                continue
            
            audio_path = self.save_audio(audio_data, user_id, i+1)
            
            if not self.verify_passphrase(audio_path):
                print("❌ Wrong phrase!")
                Path(audio_path).unlink()
                continue
            
            features = self.extract_features(audio_path)
            if features is not None:
                features_list.append(features)
                print(f"✅ Sample {i+1} accepted!")
        
        if len(features_list) < 2:
            print("❌ Need at least 2 good samples!")
            return None
        
        voiceprint = {
            'user_id': user_id,
            'features': features_list,
            'mean_feature': np.mean(features_list, axis=0)
        }
        
        voiceprint_path = VOICEPRINT_DIR / f"user_{user_id}.pkl"
        with open(voiceprint_path, 'wb') as f:
            pickle.dump(voiceprint, f)
        
        print(f"\n✅ Enrollment complete!")
        return str(voiceprint_path)
    
    def verify_user(self, user_id):
        print(f"\n{'='*50}")
        print(f"🔐 Verifying: {user_id}")
        print(f"{'='*50}")
        
        voiceprint_path = VOICEPRINT_DIR / f"user_{user_id}.pkl"
        if not voiceprint_path.exists():
            return False, 0.0
        
        with open(voiceprint_path, 'rb') as f:
            stored = pickle.load(f)
        
        audio_data = self.record_audio()
        if audio_data is None:
            return False, 0.0
        
        temp_path = self.save_audio(audio_data, "temp", None)
        
        if not self.verify_passphrase(temp_path):
            Path(temp_path).unlink()
            return False, 0.0
        
        test_features = self.extract_features(temp_path)
        Path(temp_path).unlink()
        
        if test_features is None:
            return False, 0.0
        
        similarities = [1 - cosine(feat, test_features) for feat in stored['features']]
        avg_similarity = np.mean(similarities)
        
        print(f"📊 Match: {avg_similarity:.3f} (threshold: {self.threshold})")
        
        is_match = avg_similarity > self.threshold
        print(f"\n{'✅ ACCESS GRANTED' if is_match else '❌ ACCESS DENIED'}")
        
        return is_match, avg_similarity

class VoiceLoginApp:
    def __init__(self):
        self.voice = VoiceBiometricSystem()
        
        # Setup database
        print("\n🔌 Setting up database...")
        try:
            engine = create_engine(DATABASE_URL)
            Base.metadata.create_all(engine)
            self.Session = sessionmaker(bind=engine)
            print("✅ Database ready")
        except Exception as e:
            print(f"⚠️ Database warning: {e}")
            print("Continuing without database...")
            self.Session = None
    
    def register_user(self):
        print("\n" + "="*50)
        print("📝 REGISTRATION")
        print("="*50)
        
        username = input("Username: ").strip()
        email = input("Email: ").strip()
        name = input("Full name: ").strip()
        
        if not username or not email:
            print("❌ Username and email required")
            return False
        
        # Check if user exists (if database available)
        if self.Session:
            session = self.Session()
            existing = session.query(User).filter(User.username == username).first()
            if existing:
                print(f"❌ User '{username}' exists!")
                session.close()
                return False
            session.close()
        
        # Enroll voice
        voiceprint_path = self.voice.enroll_user(username)
        
        if not voiceprint_path:
            print("❌ Enrollment failed")
            return False
        
        # Save to database if available
        if self.Session:
            try:
                session = self.Session()
                user = User(
                    username=username,
                    email=email,
                    full_name=name,
                    voiceprint_path=voiceprint_path
                )
                session.add(user)
                session.commit()
                session.close()
                print(f"\n✅ User '{username}' saved to database!")
            except Exception as e:
                print(f"⚠️ Database save error: {e}")
        
        return True
    
    def login(self):
        print("\n" + "="*50)
        print("🔐 LOGIN")
        print("="*50)
        
        username = input("Username: ").strip()
        
        if not username:
            print("❌ Username required")
            return False
        
        # Verify voice
        success, score = self.voice.verify_user(username)
        
        # Log attempt to database if available
        if self.Session:
            try:
                session = self.Session()
                attempt = LoginAttempt(
                    username=username,
                    success=success,
                    similarity_score=score
                )
                session.add(attempt)
                
                # Update failed attempts
                user = session.query(User).filter(User.username == username).first()
                if user:
                    if success:
                        user.failed_attempts = 0
                    else:
                        user.failed_attempts += 1
                
                session.commit()
                session.close()
            except:
                pass
        
        return success
    
    def list_users(self):
        if not self.Session:
            print("Database not available")
            return
        
        session = self.Session()
        users = session.query(User).all()
        
        if not users:
            print("No users found")
        else:
            print("\n👥 Users:")
            for user in users:
                print(f"  • {user.username} - {user.email}")
        
        session.close()
    
    def run(self):
        while True:
            print("\n" + "="*50)
            print("🎙️  VOICE LOGIN SYSTEM")
            print("="*50)
            print("1. Register")
            print("2. Login")
            print("3. List users")
            print("4. Exit")
            
            choice = input("\nChoice (1-4): ").strip()
            
            if choice == "1":
                self.register_user()
            elif choice == "2":
                if self.login():
                    print("\n🎉 Welcome to the system!")
            elif choice == "3":
                self.list_users()
            elif choice == "4":
                print("\nGoodbye!")
                sys.exit(0)
            else:
                print("Invalid choice")
            
            input("\nPress Enter...")

if __name__ == "__main__":
    app = VoiceLoginApp()
    app.run()