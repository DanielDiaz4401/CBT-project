import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router as simulations_router
from app.config import settings  # <-- Nueva importación
from app.db.session import SessionLocal
from app.db import models

logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Mantenemos tu lógica de Crash Recovery intacta
    logger.info(f"Iniciando {settings.PROJECT_NAME}...")
    db = SessionLocal()
    try:
        orphaned_sims = db.query(models.Simulation).filter(
            models.Simulation.status.in_([
                models.SimulationStatus.PENDING,
                models.SimulationStatus.RUNNING
            ])
        ).all()
        if orphaned_sims:
            for sim in orphaned_sims:
                sim.status = models.SimulationStatus.ERROR
                sim.error_message = "Simulation aborted due to an unexpected server restart."
            db.commit()
    finally:
        db.close()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,      # <-- Desde config.py
    description=settings.API_DESCRIPTION, # <-- Desde config.py
    version=settings.VERSION,           # <-- Desde config.py
    lifespan=lifespan,
    contact={
        "name": "Equipo de Desarrollo SRE - CBT",
        "url": "https://github.com/DanielDiaz4401/CBT-project",
    },
    license_info={
        "name": "Propiedad de CaixaBank Tech - Uso Interno",
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulations_router)