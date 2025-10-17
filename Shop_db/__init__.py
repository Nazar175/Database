from database import engine, Base
import models

print("🔧 Initializing database...")
Base.metadata.create_all(bind=engine)
print("✅ Database ready.")
