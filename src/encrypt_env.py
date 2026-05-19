from cryptography.fernet import Fernet
import json , os

secrets = {
    "GEMINI_API_KEY":os.getenv("GEMINI_API_KEY"),
    "GEMINI_API_KEY_2":os.getenv("GEMINI_API_KEY_2"),
    "GEMINI_API_KEY_3":os.getenv("GEMINI_API_KEY_3"),
    "NEW_RELIC_INSERT_KEY":os.getenv("NEW_RELIC_INSERT_KEY"),
}

key = Fernet.generate_key()
f = Fernet(key)
encrypted = f.encrypt(json.dumps(secrets).encode())

# Save these as Python files to bundle
with open("_key.bin", "wb") as kf:
    kf.write(key)
with open("_secrets.bin", "wb") as sf:
    sf.write(encrypted)
