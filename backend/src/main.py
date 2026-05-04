from fastapi import FastAPI
from app.api.endpoints import router as sim_router
from fastapi.middleware.cors import CORSMiddleware



from app.db.session import engine
from app.db.models import Base  # <--- IMPORTANTE: Importar el Base de tus modelos
from time import sleep

# Esto crea las tablas que falten
# Chapuza legendaria para que la base de datos se conecte aunque el contenedor no este activo al inicio
connected=False
while not connected:
    try:
        Base.metadata.create_all(bind=engine)
        connected=True
    except:
        sleep(1)
app = FastAPI(title="Antigravity API")

origins = [
    "http://localhost:4321",
    "http://localhost:5432",
    "http://127.0.0.1:4321",
    "http://127.0.0.1:5432",
]

# 2. Añadir el middleware a la aplicación
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Cambia a la lista 'origins' para más seguridad
    allow_credentials=True,
    allow_methods=["*"],           # Permite todos los métodos (GET, POST, DELETE, etc.)
    allow_headers=["*"],           # Permite todas las cabeceras
)

# Incluimos las rutas de simulaciones
app.include_router(sim_router)

@app.get("/")
def root():
    return {"message": "Antigravity API is running"}