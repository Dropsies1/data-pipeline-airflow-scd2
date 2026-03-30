from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

# Añadimos la carpeta principal al path para que Airflow encuentre nuestro pipeline.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importamos la función maestra que construimos
from pipeline import run_data_pipeline

# Configuración por defecto (lo que pide el archivo "Access Airflow UI.txt")
default_args = {
    'owner': 'data-engineering-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

# Definimos el DAG (Directed Acyclic Graph)
with DAG(
    'daily_data_pipeline_automation',
    default_args=default_args,
    description='Pipeline de extracción, transformación y carga (ETL)',
    schedule='@daily', # Se ejecuta todos los días a la medianoche
    catchup=False,
    tags=['etl', 'scd2', 'automation']
) as dag:

    # En Airflow, definimos "Tareas"
    # Aquí llamamos a toda nuestra función principal
    run_etl_task = PythonOperator(
        task_id='run_complete_pipeline',
        python_callable=run_data_pipeline,
    )

    # Si tuviéramos más tareas, aquí definiríamos el orden, por ejemplo:
    # extraer_tarea >> transformar_tarea >> cargar_tarea
    # Pero como centralizamos todo en run_data_pipeline(), esta es nuestra única tarea por ahora.
    
    run_etl_task