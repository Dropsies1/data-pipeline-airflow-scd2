import pandas as pd
import psycopg2
import requests
import logging
import time
from typing import List, Dict
from config import DatabaseConfig
import warnings
warnings.filterwarnings('ignore', category=UserWarning) # Silencia la advertencia de SQLAlchemy

# Configuramos el sistema de logs para registrar errores y avances
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseExtractor:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        
    def extract_customers(self, last_updated: str = None) -> pd.DataFrame:
        logger.info("Iniciando extracción de clientes desde PostgreSQL...")
        try:
            conn = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password
            )
            
            # Usamos la columna last_updated que vimos en init_database.sql
            query = "SELECT * FROM customers"
            if last_updated:
                query += f" WHERE last_updated > '{last_updated}'"
                logger.info(f"Extracción incremental: buscando registros desde {last_updated}")
            
            df = pd.read_sql(query, conn)
            conn.close()
            
            logger.info(f"Se extrajeron {len(df)} clientes exitosamente.")
            return df
            
        except Exception as e:
            logger.error(f"Error conectando a PostgreSQL: {e}")
            return pd.DataFrame()

class APIExtractor:
    def __init__(self, endpoint: str, api_key: str):
        self.endpoint = endpoint
        self.api_key = api_key
        
    def extract_orders(self, date_from: str) -> List[Dict]:
        logger.info(f"Iniciando extracción de pedidos desde API a partir de {date_from}...")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"start_date": date_from, "page": 1}
        all_orders = []
        
        while True:
            try:
                # Nota: En un entorno de prueba local, esta URL puede fallar si no hay un servidor levantado.
                response = requests.get(self.endpoint, headers=headers, params=params, timeout=10)
                
                # Manejo de Rate Limiting (Código 429)
                if response.status_code == 429:
                    logger.warning("Rate limit alcanzado. Esperando 10 segundos...")
                    time.sleep(10)
                    continue
                    
                response.raise_for_status() # Lanza error si el código no es 200
                data = response.json()
                
                # Agregamos los pedidos de esta página usando la estructura del Sample_orders.json
                if "orders" in data:
                    all_orders.extend(data["orders"])
                
                # Manejo de paginación
                if not data.get("has_more", False):
                    break
                    
                params["page"] = data.get("next_page")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error conectando a la API: {e}")
                logger.info("Usando archivo local Sample_orders.json como respaldo...")
                try:
                    import json
                    with open('./data/input/Sample_orders.json', 'r') as f:
                        backup_data = json.load(f)
                        all_orders.extend(backup_data.get("orders", []))
                except Exception as fallback_error:
                    logger.error(f"Tampoco se pudo leer el archivo de respaldo: {fallback_error}")
                break
                
        logger.info(f"Se extrajeron {len(all_orders)} pedidos en total.")
        return all_orders

class FileExtractor:
    def __init__(self, file_path: str):
        self.file_path = file_path
        
    def extract_products(self) -> pd.DataFrame:
        logger.info(f"Iniciando extracción de productos desde {self.file_path}...")
        try:
            # Leemos el archivo engañando a Pandas para que no agrupe por comillas dobles
            df = pd.read_csv(self.file_path, quotechar="'")
            
            # Limpiamos las comillas dobles (") de los nombres de las columnas
            df.columns = df.columns.str.strip('"')
            
            # Limpiamos las comillas dobles de los textos dentro de las celdas
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].str.strip('"')
            
            # Validación de calidad de datos básica
            if df.empty:
                raise ValueError("El archivo CSV está vacío.")
                
            required_columns = ['product_id', 'name', 'category', 'price']
            missing_cols = [col for col in required_columns if col not in df.columns]
            
            if missing_cols:
                raise ValueError(f"Faltan columnas requeridas en el CSV: {missing_cols}")
                
            logger.info(f"Se extrajeron {len(df)} productos exitosamente.")
            return df
            
        except FileNotFoundError:
            logger.error(f"No se encontró el archivo CSV en la ruta: {self.file_path}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error procesando el archivo CSV: {e}")
            return pd.DataFrame()