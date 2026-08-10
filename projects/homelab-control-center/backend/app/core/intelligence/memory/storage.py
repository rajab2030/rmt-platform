import json
import sqlite3
from pathlib import Path

from app.core.intelligence.memory.models import (
    MemoryRecord,
)


DB_PATH = Path("data/observability.db")


def get_connection():
    DB_PATH.parent.mkdir(
        exist_ok=True
    )

    return sqlite3.connect(
        DB_PATH
    )


def init_storage():
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS intelligence_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            component TEXT NOT NULL,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            data TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


def save_memory(
    record: MemoryRecord,
):
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO intelligence_memory
        (
            component,
            event_type,
            timestamp,
            data
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            record.component,
            record.event_type,
            record.timestamp.isoformat(),
            json.dumps(record.data),
        ),
    )

    conn.commit()
    conn.close()

    return record


def get_memory_history(component: str):

    import json

    from app.core.intelligence.memory.models import (
        MemoryRecord,
    )

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            component,
            event_type,
            timestamp,
            data
        FROM intelligence_memory
        WHERE component = ?
        ORDER BY id ASC
        """,
        (component,),
    )

    rows = cursor.fetchall()

    conn.close()

    return [
        MemoryRecord(
            component=row[0],
            event_type=row[1],
            timestamp=row[2],
            data=json.loads(row[3]),
        )
        for row in rows
    ]
