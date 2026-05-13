import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router as simulations_router
from app.db.session import SessionLocal
from app.db import models

# Configuración de log para el arranque
logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida de la aplicación.
    Se ejecuta una sola vez antes de que el servidor empiece a recibir tráfico.
    """
    logger.info("Iniciando M.I.E.R.D.A. Optimizer API...")
    logger.info("Buscando simulaciones huérfanas por reinicios inesperados...")
    
    db = SessionLocal()
    try:
        # Buscamos simulaciones que se quedaron "colgadas" en el limbo
        orphaned_sims = db.query(models.Simulation).filter(
            models.Simulation.status.in_([
                models.SimulationStatus.PENDING,
                models.SimulationStatus.RUNNING
            ])
        ).all()

        if orphaned_sims:
            logger.warning(f"¡Atención! Se encontraron {len(orphaned_sims)} simulaciones huérfanas.")
            for sim in orphaned_sims:
                sim.status = models.SimulationStatus.ERROR
                sim.error_message = "Simulation aborted due to an unexpected server restart (Crash Recovery)."
            
            db.commit()
            logger.info("Estado de simulaciones huérfanas actualizado a ERROR con éxito.")
        else:
            logger.info("No se encontraron simulaciones huérfanas. Sistema limpio.")
            
    except Exception as e:
        logger.error(f"Fallo crítico al intentar limpiar la base de datos en el arranque: {e}")
    finally:
        db.close()
        
    # El 'yield' marca el punto donde la API empieza a servir peticiones
    yield
    
    # Aquí iría la lógica de apagado controlado (Graceful Shutdown)
    logger.info("Apagando API de simulaciones...")


# Descripción detallada soportando Markdown
description = """
### CaixaBank Tech - Cloud Migration Optimization API 🚀

Esta API gestiona la lógica de negocio para la simulación de estrategias de migración de infraestructuras *on-premise* hacia entornos Cloud. 

Permite a los ingenieros evaluar el impacto en la latencia de las rutas críticas, gestionar dependencias mediante bloqueos de componentes y optimizar el despliegue por etapas cumpliendo con restricciones técnicas de capacidad y rendimiento.

#### Capacidades clave:
* **Ejecución de Algoritmos:** Simulación de procesos de migración basados en scoring de impacto.
* **Gestión de Restricciones:** Definición de componentes bloqueados hasta etapas específicas.
* **Análisis Temporal:** Desglose detallado de la evolución de latencia por cada etapa.
* **Monitoreo en Vivo:** Seguimiento de tareas mediante Server-Sent Events (SSE).
"""

app = FastAPI(
    title="CBT - Migration Optimizer API",
    description=description,
    version="1.2.0",
    lifespan=lifespan, # <-- Inyectamos el ciclo de vida aquí
    contact={
        "name": "Equipo de Desarrollo SRE - CBT",
        "url": "https://github.com/DanielDiaz4401/CBT-project",
    },
    license_info={
        "name": "Propiedad de CaixaBank Tech - Uso Interno",
    },
    openapi_tags=[
        {
            "name": "Simulations",
            "description": "Operaciones de creación, ejecución y gestión de ciclos de vida de migraciones.",
        },
    ]
)

# Configuración de seguridad y CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de rutas siguiendo la convención REST
app.include_router(simulations_router)