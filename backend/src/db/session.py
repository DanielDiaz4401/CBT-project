from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings  # <-- Nueva importación

# Usamos la URL validada por Pydantic
SQLALCHEMY_DATABASE_URL = f"postgresql://{settings.DB_USER}:{encoded_password}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

# Crear el motor (Engine)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    pool_pre_ping=True
)

# Crear la fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()