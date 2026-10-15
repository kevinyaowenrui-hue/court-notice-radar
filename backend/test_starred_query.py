import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import SessionLocal
from backend.models import CourtNotice

db = SessionLocal()
starred = db.query(CourtNotice).filter(CourtNotice.is_starred == True).all()
print("Starred count via CourtNotice.is_starred == True:", len(starred))
for s in starred:
    print(f"ID: {s.id}, Title: {s.title[:30]}, is_starred: {s.is_starred} (type: {type(s.is_starred)})")
