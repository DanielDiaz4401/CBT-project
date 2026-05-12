from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router as simulations_router

# Descripción detallada soportando Markdown
description = """
### CaixaBank Tech - Cloud Migration Optimization API 🚀

Esta API gestiona la lógica de negocio para la simulación de estrategias de migración de infraestructuras *on-premise* hacia entornos Cloud. 

Permite a los ingenieros evaluar el impacto en la latencia de las rutas críticas, gestionar dependencias mediante bloqueos de componentes y optimizar el despliegue por etapas cumpliendo con restricciones técnicas de capacidad y rendimiento.

#### Capacidades clave:
* **Ejecución de Algoritmos:** Simulación de procesos de migración basados en scoring de impacto.
* **Gestión de Restricciones:** Definición de componentes bloqueados hasta etapas específicas.
* **Análisis Temporal:** Desglose detallado de la evolución de latencia por cada etapa.
* **Monitoreo en Vivo:** Seguimiento de tareas de larga duración mediante Server-Sent Events (SSE).
"""

app = FastAPI(
    title="CBT - Migration Optimizer API",
    description=description,
    version="1.2.0",
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

# Registro de rutas siguiendo la nueva convención REST
app.include_router(simulations_router)