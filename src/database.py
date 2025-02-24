import os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from typing import List, Dict, Optional

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(os.environ['DATABASE_URL'])
        self.create_tables()

    def create_tables(self):
        with self.conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS measurement_history (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    probe_address VARCHAR(10) NOT NULL,
                    status VARCHAR(2) NOT NULL,
                    product DECIMAL(7,2) NOT NULL,
                    water DECIMAL(7,2) NOT NULL,
                    density DECIMAL(6,2) NOT NULL,
                    discriminator CHAR(1) NOT NULL,
                    temperatures JSON NOT NULL
                )
            ''')
            # Index for efficient timestamp-based queries and pagination
            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_measurement_history_timestamp 
                ON measurement_history (timestamp DESC)
            ''')
            self.conn.commit()

    def save_measurement(self, probe_data: Dict):
        with self.conn.cursor() as cur:
            cur.execute('''
                INSERT INTO measurement_history 
                (timestamp, probe_address, status, product, water, density, discriminator, temperatures)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                datetime.strptime(probe_data['datetime'], '%Y-%m-%d %H:%M:%S'),
                probe_data['address'],
                probe_data['status'],
                float(probe_data['product']),
                float(probe_data['water']),
                float(probe_data['density']),
                probe_data['discriminator'],
                json.dumps(probe_data['temperatures'])  # Convert list to JSON string
            ))
            self.conn.commit()

    def get_measurement_history(self, page: int = 1, per_page: int = 200) -> tuple[List[Dict], int]:
        offset = (page - 1) * per_page
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get total count
            cur.execute('SELECT COUNT(*) as count FROM measurement_history')
            total_records = cur.fetchone()['count']

            # Get paginated results
            cur.execute('''
                SELECT * FROM measurement_history
                WHERE timestamp >= NOW() - INTERVAL '1 week'
                ORDER BY timestamp DESC
                LIMIT %s OFFSET %s
            ''', (per_page, offset))
            records = cur.fetchall()

        return list(records), total_records

    def cleanup_old_records(self):
        """Remove records older than 1 week"""
        with self.conn.cursor() as cur:
            cur.execute('''
                DELETE FROM measurement_history
                WHERE timestamp < NOW() - INTERVAL '1 week'
            ''')
            self.conn.commit()