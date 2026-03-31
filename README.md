# Data Pipeline Automation System (ETL)
## Descripción del Proyecto
Este proyecto es un pipeline de datos (ETL) automatizado de extremo a extremo, diseñado para consolidar información de múltiples fuentes (bases de datos SQL, APIs y archivos CSV) en un Data Warehouse centralizado. 

El objetivo es limpiar y transformar los datos en bruto para generar una Tabla de Hechos (Fact Table) de ventas diarias, manteniendo el historial completo de cambios en la dimensión de clientes mediante la implementación de Slowly Changing Dimensions (SCD) Tipo 2. Todo el flujo de trabajo está orquestado mediante Apache Airflow.

## Tecnologías y Herramientas
* **Lenguaje:** Python 3
* **Orquestación:** Apache Airflow
* **Base de Datos:** PostgreSQL
* **Procesamiento de Datos:** Pandas
* **Integración:** Requests (API Rest)
* **Control de Versiones:** Git & GitHub

## Características Principales
1. **Extracción Multifuente:** Extracción incremental de clientes desde PostgreSQL, ingesta de CSV de productos con limpieza de formatos, y consumo de pedidos vía API REST (con mecanismo de fallback a JSON local).
2. **Calidad de Datos:** Validación de nulos, limpieza de strings atípicos y generación de reportes de calidad en consola mediante la librería `logging`.
3. **Modelado Histórico (SCD Tipo 2):** Implementación de lógica SCD2 en Pandas para rastrear cambios en los clientes, gestionando automáticamente fechas de caducidad (`effective_end_date`) y estados activos (`is_current`).
4. **Carga y Agregación:** Agrupación de pedidos a nivel diario para alimentar la tabla `fact_daily_orders` con métricas clave (ventas totales, ticket promedio) e inserción transaccional segura en PostgreSQL.

## Estructura del Proyecto

```text
project/
├── dags/
│   └── airflow_dag.py          # Definición del flujo de trabajo en Airflow
├── data/
│   ├── input/                  # Datos crudos (CSV de productos, Sample Orders JSON)
│   └── output/
├── config.py                   # Gestión segura de credenciales mediante .env
├── extractors.py               # Módulos conectores a API, Postgres y File System
├── transformers.py             # Lógica de validación, limpieza y SCD2
├── pipeline.py                 # Script maestro (Director del proceso ETL)
├── Requirements.txt            # Dependencias del proyecto
├── .env.example                # Plantilla de variables de entorno
└── README.md
````

## Instrucciones de Instalación y Ejecución

### 1. Preparar el Entorno

Se recomienda usar un entorno virtual:

Bash

```
python -m venv venv
source venv/bin/activate
pip install -r Requirements.txt
```

### 2. Configuración Inicial

- Asegúrate de tener PostgreSQL corriendo e inicializa las tablas con tu script SQL.
    
- Crea un archivo oculto `.env` en la raíz del proyecto basándote en la plantilla `.env.example` y configura tus credenciales locales.
    

### 3. Prueba del Pipeline (Manual)

Verifica que el código extrae, transforma y carga los datos correctamente en la base de datos:

Bash

```
python pipeline.py
```

### 4. Orquestación con Apache Airflow

Configura las rutas para que Airflow detecte el DAG en tu carpeta local y levanta los servicios:

Bash

```
export AIRFLOW_HOME=$(pwd)
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/dags
airflow standalone
```
![Captura de Airflow exitosa](NOMBRE_DE_TU_IMAGEN.png)
1. Abre tu navegador y accede a `http://localhost:8080`.
    
2. Inicia sesión con el usuario `admin` (la contraseña se genera en la terminal o puedes resetearla manualmente).
    
3. Busca el DAG `daily_data_pipeline_automation`, desactiva la pausa y presiona **Trigger DAG** para iniciar la ejecución automatizada.
