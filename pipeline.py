import logging
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from config import load_config
from extractors import DatabaseExtractor, APIExtractor, FileExtractor
from transformers import DataValidator, SCD2Processor
import warnings

# Silenciamos advertencias de Pandas
warnings.filterwarnings('ignore')

# Configuramos el registro de eventos (Logs)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection(config):
    """Crea una conexión a PostgreSQL"""
    return psycopg2.connect(
        host=config.host, port=config.port,
        database=config.database, user=config.username, password=config.password
    )

def run_data_pipeline():
    logger.info("=== INICIANDO PIPELINE DE DATOS ===")
    
    # ---------------------------------------------------------
    # 1. CARGAR CONFIGURACIÓN
    # ---------------------------------------------------------
    config = load_config()
    
    # Instanciamos nuestras herramientas
    db_extractor = DatabaseExtractor(config.database)
    api_extractor = APIExtractor(config.api_endpoint, config.api_key)
    file_extractor = FileExtractor(f"{config.input_path}/products.csv")
    
    validator = DataValidator()
    scd2_processor = SCD2Processor()

    # ---------------------------------------------------------
    # 2. EXTRACCIÓN
    # ---------------------------------------------------------
    logger.info("--- Fase de Extracción ---")
    df_customers = db_extractor.extract_customers()
    df_products_raw = file_extractor.extract_products()
    
    # En un caso real usaríamos la fecha de ayer. Usamos 2024-02-01 porque es la del Sample_orders.json
    orders_list = api_extractor.extract_orders('2024-02-01') 
    
    # ---------------------------------------------------------
    # 3. TRANSFORMACIÓN Y LIMPIEZA
    # ---------------------------------------------------------
    logger.info("--- Fase de Transformación ---")
    
    # Validar y limpiar productos
    validator.validate_data_quality(df_products_raw, 'products_raw')
    df_products = validator.clean_products(df_products_raw)
    
    # Lógica SCD2 para Clientes
    conn = get_db_connection(config.database)
    # Extraemos el historial actual para comparar
    try:
        df_existing_dim = pd.read_sql("SELECT * FROM dim_customers", conn)
    except Exception:
        df_existing_dim = pd.DataFrame() # Si la tabla está vacía o falla
        
    records_to_insert, records_to_update = scd2_processor.apply_scd2_logic(df_customers, df_existing_dim)
    
    # Transformar Pedidos (Crear Fact Table de ventas diarias)
    df_fact_orders = pd.DataFrame()
    if orders_list:
        df_orders = pd.DataFrame(orders_list)
        # Agrupamos por fecha y cliente para calcular métricas diarias
        df_fact_orders = df_orders.groupby(['order_date', 'customer_id']).agg(
            total_sales=('total_amount', 'sum'),
            order_count=('order_id', 'count'),
            unique_orders=('order_id', 'nunique')
        ).reset_index()
        # Calculamos el valor promedio del pedido
        df_fact_orders['avg_order_value'] = df_fact_orders['total_sales'] / df_fact_orders['order_count']
        logger.info(f"Se generaron {len(df_fact_orders)} registros para la tabla de hechos (Fact Table).")

    # ---------------------------------------------------------
    # 4. CARGA A POSTGRESQL (Load)
    # ---------------------------------------------------------
    logger.info("--- Fase de Carga ---")
    cursor = conn.cursor()
    
    try:
        # A) Actualizar registros SCD2 viejos (caducarlos)
        if not records_to_update.empty:
            for _, row in records_to_update.iterrows():
                cursor.execute("""
                    UPDATE dim_customers 
                    SET effective_end_date = %s, is_current = %s 
                    WHERE dim_customer_key = %s
                """, (row['effective_end_date'], row['is_current'], row['dim_customer_key']))
            logger.info(f"Se caducaron {len(records_to_update)} registros históricos en dim_customers.")

        # B) Insertar nuevos registros SCD2
        if not records_to_insert.empty:
            insert_query = """
                INSERT INTO dim_customers 
                (customer_id, name, email, status, effective_start_date, effective_end_date, is_current)
                VALUES %s
            """
            # Preparamos los datos como una lista de tuplas
            values = records_to_insert[['customer_id', 'name', 'email', 'status', 'effective_start_date', 'effective_end_date', 'is_current']].values.tolist()
            execute_values(cursor, insert_query, values)
            logger.info(f"Se insertaron {len(records_to_insert)} nuevos registros en dim_customers.")

        # C) Insertar en Fact Table
        if not df_fact_orders.empty:
            fact_query = """
                INSERT INTO fact_daily_orders 
                (order_date, customer_id, total_sales, order_count, avg_order_value, unique_orders)
                VALUES %s
                ON CONFLICT (order_date, customer_id) DO NOTHING;
            """
            fact_values = df_fact_orders[['order_date', 'customer_id', 'total_sales', 'order_count', 'avg_order_value', 'unique_orders']].values.tolist()
            execute_values(cursor, fact_query, fact_values)
            logger.info("Se cargaron las ventas diarias en fact_daily_orders.")

        conn.commit()
        logger.info("Cambios guardados en la base de datos exitosamente.")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error durante la carga a la base de datos: {e}")
    finally:
        cursor.close()
        conn.close()

    # ---------------------------------------------------------
    # 5. REPORTE FINAL DE CALIDAD
    # ---------------------------------------------------------
    logger.info("=== REPORTE DE CALIDAD DE DATOS ===")
    for table, metrics in validator.validation_results.items():
        estado = "PASÓ" if metrics['passed_validation'] else "FALLÓ"
        logger.info(f"Tabla: {table} | Filas: {metrics['total_rows']} | Estado: {estado}")
        
    logger.info("=== PIPELINE FINALIZADO ===")

if __name__ == "__main__":
    run_data_pipeline()