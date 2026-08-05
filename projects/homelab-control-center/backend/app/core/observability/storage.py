import sqlite3
from pathlib import Path


DB_PATH = Path("data/observability.db")


def get_connection():

    DB_PATH.parent.mkdir(
        exist_ok=True
    )

    return sqlite3.connect(DB_PATH)


def init_storage():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS container_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT,
            cpu_usage REAL,
            memory_usage INTEGER,
            health TEXT,
            timestamp TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()

def save_container_metric(metric):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO container_metrics
        (
            name,
            status,
            cpu_usage,
            memory_usage,
            health,
            timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            metric.name,
            metric.status,
            metric.cpu_usage,
            metric.memory_usage,
            metric.health,
            metric.timestamp.isoformat(),
        ),
    )

    conn.commit()
    conn.close()


def get_container_metrics(limit=50):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            name,
            status,
            cpu_usage,
            memory_usage,
            health,
            timestamp
        FROM container_metrics
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


def get_latest_container_metrics():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            name,
            status,
            cpu_usage,
            memory_usage,
            health,
            timestamp
        FROM container_metrics
        WHERE id IN (
            SELECT MAX(id)
            FROM container_metrics
            GROUP BY name
        )
        ORDER BY name
        """
    )

    rows = cursor.fetchall()

    conn.close()

    return rows
