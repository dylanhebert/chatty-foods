import db
from app import app

db.init_db()
db.sync_all()
