import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

# Construir la URL de conexión
# Formato: postgresql://usuario:password@host:puerto/nombre_db
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    # Fallback por si olvidas configurar el .env (solo para desarrollo local)
    SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost:5432/antigravity_db"

# 1. Crear el motor (Engine)
# 'pool_pre_ping' ayuda a recuperar la conexión si se cae el servidor de DB
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    pool_pre_ping=True
)

# 2. Crear la fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Dependencia para FastAPI
def get_db():
    """
    Crea una nueva sesión de base de datos para cada petición
    y la cierra automáticamente al terminar.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()