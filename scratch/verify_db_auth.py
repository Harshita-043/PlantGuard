# Verify DB connection and JWT handling
import os, json
from pathlib import Path
import psycopg
import jwt

# Load env variables from backend/.env (simple parser)
env_path = Path('backend/.env')
env = {}
for line in env_path.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    if '=' in line:
        key, val = line.split('=', 1)
        env[key.strip()] = val.strip()

# DB test
db_url = env.get('DATABASE_URL')
print('DATABASE_URL is set:', bool(db_url))
try:
    # use psycopg.connect
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
            result = cur.fetchone()
            print('DB SELECT result:', result)
except Exception as e:
    print('DB connection FAILED:', type(e).__name__)

# JWT test
secret = env.get('JWT_SECRET_KEY')
print('JWT secret present:', bool(secret))
payload = {'sub': 'test_user', 'exp': 9999999999}
try:
    token = jwt.encode(payload, secret, algorithm='HS256')
    print('Sample token generated: True')
    decoded = jwt.decode(token, secret, algorithms=['HS256'])
    print('Decoded payload sub:', decoded.get('sub'))
except Exception as e:
    print('JWT encode/decode FAILED:', type(e).__name__)

