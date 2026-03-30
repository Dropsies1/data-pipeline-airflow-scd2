import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()  # Carga las variables de entorno desde el archivo .env

@dataclass
class DatabaseConfig:
    host: str
    port: int
    database: str
    username: str
    password: str
    
@dataclass
class PipelineConfig:
    database: DatabaseConfig
    api_endpoint: str
    api_key: str
    input_path: str
    output_path: str
    batch_size: int = 1000
    
def load_config() -> PipelineConfig:
    # Creamos la configuración de la base de datos leyendo variables de entorno
    # Si no encuentra la variable, usa un valor por defecto (ej. "localhost")
    db_config = DatabaseConfig(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "pipeline_db"),
        username=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "secure_password")
    )
    
    # Armamos la configuración general del pipeline
    return PipelineConfig(
        database=db_config,
        api_endpoint=os.getenv("API_ENDPOINT", "https://api.mock.com/orders"),
        api_key=os.getenv("API_KEY", "clave_secreta_123"),
        input_path=os.getenv("INPUT_PATH", "./data/"),
        output_path=os.getenv("OUTPUT_PATH", "./output/"),
        batch_size=int(os.getenv("BATCH_SIZE", 1000))
    )