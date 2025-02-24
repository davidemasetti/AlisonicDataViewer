import os
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from typing import List, Dict, Optional
import streamlit as st

class Database:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(os.environ['DATABASE_URL'])
            self.create_tables()
        except Exception as e:
            st.error(f"Database connection error: {str(e)}")
            raise

    def create_tables(self):
        with self.conn.cursor() as cur:
            try:
                # Create the measurement_history table if it doesn't exist
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
                # Create index for efficient timestamp-based queries
                cur.execute('''
                    CREATE INDEX IF NOT EXISTS idx_measurement_history_timestamp 
                    ON measurement_history (timestamp DESC)
                ''')
                self.conn.commit()
            except Exception as e:
                st.error(f"Error creating tables: {str(e)}")
                self.conn.rollback()
                raise

    def save_measurement(self, probe_data: Dict):
        try:
            with self.conn.cursor() as cur:
                # Check if measurement already exists for this timestamp
                cur.execute('''
                    SELECT COUNT(*) FROM measurement_history 
                    WHERE timestamp = %s AND probe_address = %s
                ''', (
                    datetime.strptime(probe_data['datetime'], '%Y-%m-%d %H:%M:%S'),
                    probe_data['address']
                ))

                if cur.fetchone()[0] == 0:  # Only insert if measurement doesn't exist
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
                        json.dumps(probe_data['temperatures'])
                    ))
                    self.conn.commit()
        except Exception as e:
            st.error(f"Error saving measurement: {str(e)}")
            self.conn.rollback()
            raise

    def get_measurement_history(self, page: int = 1, per_page: int = 200) -> tuple[List[Dict], int]:
        try:
            offset = (page - 1) * per_page
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get total count
                cur.execute('SELECT COUNT(*) as count FROM measurement_history')
                result = cur.fetchone()
                total_records = result['count'] if result else 0

                # Get paginated results
                cur.execute('''
                    SELECT 
                        timestamp, probe_address, status, 
                        product, water, density, discriminator
                    FROM measurement_history
                    ORDER BY timestamp DESC
                    LIMIT %s OFFSET %s
                ''', (per_page, offset))
                records = cur.fetchall()

                return list(records), total_records
        except Exception as e:
            st.error(f"Error fetching measurement history: {str(e)}")
            return [], 0