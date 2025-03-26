import os

from dotenv import load_dotenv
import psycopg2


def load_database_config():

    load_dotenv()
    host = os.getenv('DB_HOST', 'localhost')
    port = int(os.getenv('DB_PORT', 5432))
    username = os.getenv('DB_USERNAME', 'postgres')
    password = os.getenv('DB_PASSWORD', 'root')
    dbname = os.getenv('DB_NAME', 'eny')

    return {
        'host': host,
        'port': port,
        'username': username,
        'password': password,
        'dbname': dbname
    }

def database_connection():
    config = load_database_config()
    psql_info = (
        f"host={config['host']} port={config['port']} user={'postgres'} "
        f"password={config['password']} dbname={config['dbname']} "
        f"options='-c client_encoding=UTF8'"
    )
    try:
        conn = psycopg2.connect(psql_info)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        print("Success")
        return conn
    except psycopg2.Error as err:
        print(f"Error connecting to the database: {err}")
        return None

