from config import load_config
from extractors import DatabaseExtractor, FileExtractor
import json

# 1. Cargamos la configuración segura (tu archivo .env)
config = load_config()

# 2. Probamos la Base de Datos
print("\n--- PROBANDO POSTGRESQL ---")
db_extractor = DatabaseExtractor(config.database)
clientes_df = db_extractor.extract_customers()
print(clientes_df.head())

# 3. Probamos el CSV
print("\n--- PROBANDO CSV DE PRODUCTOS ---")
file_extractor = FileExtractor(config.input_path + "/products.csv") # Asumiendo que renombraste el archivo
productos_df = file_extractor.extract_products()
print(productos_df.head())