"""
Biometric Data Security & Encryption Service
Implements AES-256 (Fernet) encryption at rest for biometric embeddings,
registration burst frames, and profile photos.
Complies with university data protection policies and Nepal Individual Privacy Act 2018.
"""

import os
import base64
import json
import numpy as np
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Master Key Management
DEFAULT_SALT = b"northfield_attendance_security_salt_2026"
MASTER_KEY_ENV = os.getenv("BIOMETRIC_MASTER_KEY", "northfield-production-attendance-secure-key-2026-october")

def derive_fernet_key(passphrase: str, salt: bytes = DEFAULT_SALT) -> bytes:
    """Derives a deterministic, cryptographically secure 32-byte key for Fernet AES-256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))
    return key

class BiometricSecurityEngine:
    def __init__(self, master_passphrase: str = MASTER_KEY_ENV):
        self._key = derive_fernet_key(master_passphrase)
        self._cipher = Fernet(self._key)

    def encrypt_bytes(self, raw_data: bytes) -> bytes:
        """Encrypts arbitrary binary bytes (e.g., JPEG crops) at rest."""
        if not raw_data:
            return b""
        return self._cipher.encrypt(raw_data)

    def decrypt_bytes(self, cipher_data: bytes) -> bytes:
        """Decrypts encrypted binary bytes."""
        if not cipher_data:
            return b""
        return self._cipher.decrypt(cipher_data)

    def encrypt_embedding(self, embedding_vector: np.ndarray) -> bytes:
        """Encrypts a 128-D normalized float32 numpy vector."""
        if embedding_vector is None:
            return b""
        flat = np.asarray(embedding_vector, dtype=np.float32).flatten()
        raw_bytes = flat.tobytes()
        return self._cipher.encrypt(raw_bytes)

    def decrypt_embedding(self, cipher_data: bytes, dim: int = 128) -> np.ndarray:
        """Decrypts cipher bytes back to a normalized float32 numpy vector."""
        if not cipher_data:
            return np.zeros((dim,), dtype=np.float32)
        decrypted_raw = self._cipher.decrypt(cipher_data)
        return np.frombuffer(decrypted_raw, dtype=np.float32).copy()

    def encrypt_file(self, source_path: Path, dest_encrypted_path: Path) -> bool:
        """Reads a local image file, encrypts it, and writes encrypted file to destination."""
        try:
            with open(source_path, "rb") as f:
                data = f.read()
            encrypted = self.encrypt_bytes(data)
            dest_encrypted_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_encrypted_path, "wb") as f:
                f.write(encrypted)
            return True
        except Exception as e:
            print(f"[BiometricSecurity] Failed to encrypt file {source_path}: {e}")
            return False

    def decrypt_file(self, encrypted_path: Path) -> bytes:
        """Reads an encrypted file from disk and returns raw decrypted bytes (e.g. for image decoding)."""
        try:
            with open(encrypted_path, "rb") as f:
                data = f.read()
            return self.decrypt_bytes(data)
        except Exception as e:
            print(f"[BiometricSecurity] Failed to decrypt file {encrypted_path}: {e}")
            return b""

# Global Singleton
security_engine = BiometricSecurityEngine()
