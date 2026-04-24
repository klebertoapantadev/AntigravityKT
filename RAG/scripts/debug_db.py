import os
import psycopg2
from dotenv import load_dotenv

# Configuración manual de conexión (datos de detalles.md)
DB_NAME = "postgres"
DB_USER = "postgres.ufnpzxlvpwagavoytwco"
DB_PASS = "IMUm7zBFmxNuggNj"
DB_HOST = "aws-0-us-east-1.pooler.supabase.com" # Host común para Supabase
DB_PORT = "6543"

try:
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    cur = conn.cursor()
    
    # Verificar esquemas
    cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'rag';")
    schema_exists = cur.fetchone()
    print(f"Esquema 'rag' existe: {schema_exists is not None}")
    
    if schema_exists:
        # Verificar tablas
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'rag';")
        tables = cur.fetchall()
        print(f"Tablas en 'rag': {[t[0] for t in tables]}")
        
        # Verificar colecciones
        cur.execute("SELECT name, created_at FROM rag.collections ORDER BY created_at DESC LIMIT 5;")
        cols = cur.fetchall()
        print(f"Últimas colecciones: {cols}")
        
        # Verificar vectores
        cur.execute("SELECT count(*) FROM rag.vectors;")
        count = cur.fetchone()[0]
        print(f"Total de vectores en rag.vectors: {count}")

    cur.close()
    conn.close()
except Exception as e:
    print(f"Error conectando a DB: {e}")
