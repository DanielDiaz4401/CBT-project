from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Metadatos de la API
    PROJECT_NAME: str = "CBT - Migration Optimizer API"
    VERSION: str = "1.2.0"
    
    # Configuración de Base de Datos
    # El campo es obligatorio, si no está en el .env, la app no arrancará
    DB_USER: str = Field(..., validation_alias="DB_USER")
    DB_PASSWORD: str = Field(..., validation_alias="DB_PASSWORD")
    DB_HOST: str = Field(..., validation_alias="DB_HOST")
    DB_PORT: str = Field(..., validation_alias="DB_PORT")
    DB_NAME: str = Field(..., validation_alias="DB_NAME")

    # Documentación (Movemos aquí el Markdown de main.py)
    API_DESCRIPTION: str = """
### CaixaBank Tech - Cloud Migration Optimization API 🚀

Esta API gestiona la lógica de negocio para la simulación de estrategias de migración de infraestructuras *on-premise* hacia entornos Cloud. 

#### Capacidades clave:
* **Ejecución de Algoritmos:** Simulación basada en scoring de impacto.
* **Gestión de Restricciones:** Definición de componentes bloqueados.
* **Monitoreo en Vivo:** Seguimiento mediante Server-Sent Events (SSE).
"""

    # Configuración del archivo .env
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instancia global para ser importada en el resto del proyecto
settings = Settings()