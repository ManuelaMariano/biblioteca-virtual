# Módulo de acesso ao banco de dados.
# Mantido para uma etapa futura; o app.py desta atividade ainda não usa MySQL.

import mysql.connector
from mysql.connector import Error, pooling

_DB_PARAMS = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'bibliotecavirtual',
    'charset': 'utf8mb4',
    'sql_mode': ('STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,'
                 'ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'),
    'time_zone': '-03:00',
    'use_pure': True,
    'connection_timeout': 10,
    'autocommit': False,
}

_pool = pooling.MySQLConnectionPool(
    pool_name='webapp_pool',
    pool_size=5,
    pool_reset_session=True,
    **_DB_PARAMS
)


def get_connection():
    try:
        return _pool.get_connection()
    except Error as e:
        raise Exception(f'Não foi possível obter conexão do pool: {e}')


def execute_query(sql, params=None, fetch=False):
    conn = get_connection()
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        if fetch:
            return cursor.fetchall()
        conn.commit()
        return cursor.rowcount
    except Error as e:
        conn.rollback()
        raise Exception(f'Erro ao executar query: {e}')
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


def execute_one(sql, params=None):
    resultados = execute_query(sql, params, fetch=True)
    return resultados[0] if resultados else None
