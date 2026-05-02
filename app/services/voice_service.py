import os
import pickle
from pathlib import Path
import numpy as np
import torch
import torchaudio
from scipy.spatial.distance import cosine
import speech_recognition as sr
from speechbrain.pretrained import EncoderClassifier


class VoiceService:
    def __init__(self, config):
        self.sample_rate = config["SAMPLE_RATE"]
        self.threshold = config["SPEAKER_THRESHOLD"]
        self.voiceprint_dir = Path(config["VOICEPRINT_DIR"])
        self.model_source = config["SPEECHBRAIN_MODEL"]
        self._encoder = None

    def _get_encoder(self):
        if self._encoder is None:
            self._encoder = EncoderClassifier.from_hparams(
                source=self.model_source, run_opts={"device": "cpu"}
            )
        return self._encoder

    def _load_audio(self, audio_path):
        wav, sr = torchaudio.load(audio_path)
        if wav.shape[0] > 1:
            wav = torch.mean(wav, dim=0, keepdim=True)
        if sr != self.sample_rate:
            wav = torchaudio.functional.resample(wav, sr, self.sample_rate)
        return wav

    def extract_embedding(self, audio_path):
        wav = self._load_audio(audio_path)
        encoder = self._get_encoder()
        with torch.no_grad():
            embedding = encoder.encode_batch(wav).squeeze(0).squeeze(0)
        return embedding.cpu().numpy()

    def enroll_user(self, user_id, audio_paths):
        embeddings = []
        for audio_path in audio_paths:
            embedding = self.extract_embedding(audio_path)
            embeddings.append(embedding)

        mean_embedding = np.mean(embeddings, axis=0)
        voiceprint = {
            "user_id": user_id,
            "embeddings": embeddings,
            "mean_embedding": mean_embedding,
        }

        voiceprint_path = self.voiceprint_dir / f"user_{user_id}.pkl"
        with open(voiceprint_path, "wb") as handle:
            pickle.dump(voiceprint, handle)

        return str(voiceprint_path)

    def identify_speaker(self, audio_path):
        if not self.voiceprint_dir.exists():
            return None, 0.0

        test_embedding = self.extract_embedding(audio_path)
        best_user_id = None
        best_score = 0.0

        for file_name in os.listdir(self.voiceprint_dir):
            if not file_name.endswith(".pkl"):
                continue
            file_path = self.voiceprint_dir / file_name
            with open(file_path, "rb") as handle:
                stored = pickle.load(handle)

            mean_embedding = stored.get("mean_embedding")
            if mean_embedding is None:
                continue

            score = 1 - cosine(mean_embedding, test_embedding)
            if score > best_score:
                best_score = score
                best_user_id = stored.get("user_id")

        return best_user_id, float(best_score)

    def verify_speaker(self, user_id, audio_path):
        voiceprint_path = self.voiceprint_dir / f"user_{user_id}.pkl"
        if not voiceprint_path.exists():
            return False, 0.0

        with open(voiceprint_path, "rb") as handle:
            stored = pickle.load(handle)

        mean_embedding = stored.get("mean_embedding")
        if mean_embedding is None:
            return False, 0.0

        test_embedding = self.extract_embedding(audio_path)
        score = 1 - cosine(mean_embedding, test_embedding)
        return score >= self.threshold, float(score)

    def _normalize_text(self, text):
        return " ".join("".join(ch for ch in text.lower() if ch.isalnum() or ch.isspace()).split())

    def verify_passphrase(self, audio_path, expected_phrase):
        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(audio_path) as source:
                audio = recognizer.record(source)
            transcript = recognizer.recognize_google(audio)
        except Exception:
            return False, None

        normalized_transcript = self._normalize_text(transcript)
        normalized_expected = self._normalize_text(expected_phrase)

        # Strict exact match after normalization. Do NOT accept partial or fuzzy matches.
        match = normalized_transcript == normalized_expected

        # Return normalized transcript for clearer debugging on the caller side.
        return match, normalized_transcript
