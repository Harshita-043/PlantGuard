from sqlalchemy import create_engine
url = "postgresql://postgres:harshita@localhost:5432/plantguard"
try:
    engine = create_engine(url)
    print("Engine created:", engine)
except Exception as e:
    print("Engine error:", e)

