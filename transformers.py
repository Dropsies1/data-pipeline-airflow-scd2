import pandas as pd
from datetime import datetime
from typing import Tuple, Dict, Any
import logging

# Configuramos el sistema de logs
logger = logging.getLogger(__name__)

class DataValidator:
    def __init__(self):
        self.validation_results = {}
        
    def clean_products(self, df: pd.DataFrame) -> pd.DataFrame:
        """Limpia las comillas rebeldes de los productos y convierte tipos de datos."""
        logger.info("Limpiando datos de productos...")
        df_clean = df.copy()
        
        # Quitamos comillas sobrantes
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                df_clean[col] = df_clean[col].str.strip('"')
        
        # Convertimos el precio a un número matemático (float)
        if 'price' in df_clean.columns:
            df_clean['price'] = pd.to_numeric(df_clean['price'], errors='coerce')
            
        return df_clean

    def validate_data_quality(self, data: pd.DataFrame, table_name: str) -> Dict[str, Any]:
        """Verifica que los datos cumplan con las reglas de negocio antes de guardarlos."""
        logger.info(f"Validando calidad de datos para: {table_name}")
        
        total_rows = len(data)
        null_counts = data.isnull().sum().to_dict()
        total_nulls = sum(null_counts.values())
        
        # Regla 1: No debe haber datos nulos
        passed = total_nulls == 0
        
        # Regla 2: Si son productos, el precio no puede ser negativo
        if table_name == 'products' and 'price' in data.columns:
            negative_prices = (data['price'] < 0).sum()
            if negative_prices > 0:
                passed = False
                logger.warning(f"¡Alerta! Se encontraron {negative_prices} productos con precio negativo.")

        metrics = {
            "table": table_name,
            "total_rows": total_rows,
            "null_counts": null_counts,
            "passed_validation": passed
        }
        
        if not passed:
            logger.error(f"La validación falló para {table_name}. Métricas: {metrics}")
        else:
            logger.info(f"Validación exitosa para {table_name}.")
            
        self.validation_results[table_name] = metrics
        return metrics

class SCD2Processor:
    def __init__(self, connection=None):
        self.connection = connection
        
    def apply_scd2_logic(self, new_data: pd.DataFrame, existing_data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        La magia del SCD Tipo 2: Compara los datos frescos con el historial.
        Devuelve dos cosas:
        1. records_to_insert: Clientes nuevos o actualizaciones que deben registrarse hoy.
        2. records_to_update: Registros viejos que deben ser 'caducados'.
        """
        logger.info("Aplicando lógica SCD Tipo 2 a los clientes...")
        
        today = datetime.now().date()
        # Fecha infinita para los registros que están activos actualmente
        end_of_time = pd.to_datetime('9999-12-31').date()
        
        # Escenario 1: La tabla de historial está vacía (primera vez que corremos el pipeline)
        if existing_data is None or existing_data.empty:
            inserts = new_data.copy()
            inserts['effective_start_date'] = today
            inserts['effective_end_date'] = end_of_time
            inserts['is_current'] = True
            return inserts, pd.DataFrame()

        # Comparamos los datos nuevos con los registros que actualmente están activos
        active_existing = existing_data[existing_data['is_current'] == True]
        merged = pd.merge(new_data, active_existing, on='customer_id', how='left', suffixes=('', '_old'))
        
        # Escenario 2: Clientes completamente nuevos
        new_customers = merged[merged['dim_customer_key'].isna()].copy()
        cols_to_keep = list(new_data.columns)
        new_customers = new_customers[cols_to_keep]
        new_customers['effective_start_date'] = today
        new_customers['effective_end_date'] = end_of_time
        new_customers['is_current'] = True

        # Escenario 3: Clientes que ya existían pero cambiaron su nombre, email o estado
        existing_mask = merged['dim_customer_key'].notna()
        changed_mask = existing_mask & (
            (merged['name'] != merged['name_old']) |
            (merged['email'] != merged['email_old']) |
            (merged['status'] != merged['status_old'])
        )
        changed_customers = merged[changed_mask].copy()
        
        records_to_update = pd.DataFrame()
        updated_inserts = pd.DataFrame()
        
        if not changed_customers.empty:
            # A los registros viejos les ponemos fecha de fin de hoy y los marcamos inactivos
            records_to_update = changed_customers[['dim_customer_key']].copy()
            records_to_update['effective_end_date'] = today
            records_to_update['is_current'] = False
            
            # Creamos la "nueva versión" de esos clientes con los datos actualizados
            updated_inserts = changed_customers[cols_to_keep].copy()
            updated_inserts['effective_start_date'] = today
            updated_inserts['effective_end_date'] = end_of_time
            updated_inserts['is_current'] = True
            
        # Juntamos los nuevos clientes con las versiones actualizadas de los viejos
        records_to_insert = pd.concat([new_customers, updated_inserts], ignore_index=True)
        
        logger.info(f"Resultados SCD2: {len(records_to_insert)} filas para insertar, {len(records_to_update)} filas viejas para caducar.")
        return records_to_insert, records_to_update