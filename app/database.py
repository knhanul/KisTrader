import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Generator, Dict, Any

from app.config import settings


def get_database_config() -> Dict[str, str]:
    return {
        "host": settings.db_host,
        "port": settings.db_port,
        "dbname": settings.db_name,
        "user": settings.db_user,
        "password": settings.db_password,
        "sslmode": settings.db_sslmode,
    }


@contextmanager
def get_db_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    conn = None
    try:
        conn = psycopg2.connect(**get_database_config())
        yield conn
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


@contextmanager
def get_db_cursor() -> Generator[psycopg2.extensions.cursor, None, None]:
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            conn.commit()
        except psycopg2.Error as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()


def execute_query(query: str, params: tuple = None) -> list[Dict[str, Any]]:
    with get_db_cursor() as cursor:
        cursor.execute(query, params or ())
        return cursor.fetchall()


def execute_single_query(query: str, params: tuple = None) -> Dict[str, Any]:
    with get_db_cursor() as cursor:
        cursor.execute(query, params or ())
        return cursor.fetchone()


def execute_update(query: str, params: tuple = None) -> int:
    with get_db_cursor() as cursor:
        cursor.execute(query, params or ())
        return cursor.rowcount


def test_connection() -> bool:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
    except psycopg2.Error:
        return False
