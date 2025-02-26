import os
from datetime import datetime
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
                # Create clients table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS clients (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Create sites table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS sites (
                        id SERIAL PRIMARY KEY,
                        client_id INTEGER NOT NULL REFERENCES clients(id),
                        name VARCHAR(100) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(client_id, name)
                    )
                ''')

                # Create probes table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS probes (
                        id SERIAL PRIMARY KEY,
                        site_id INTEGER NOT NULL REFERENCES sites(id),
                        probe_address VARCHAR(10) NOT NULL UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Create measurements table with foreign key to probes
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS measurements (
                        id SERIAL PRIMARY KEY,
                        probe_id INTEGER NOT NULL REFERENCES probes(id),
                        timestamp TIMESTAMP NOT NULL,
                        status VARCHAR(2) NOT NULL,
                        product DECIMAL(7,2) NOT NULL,
                        water DECIMAL(7,2) NOT NULL,
                        density DECIMAL(6,2) NOT NULL,
                        discriminator CHAR(1) NOT NULL,
                        temperatures JSON NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(probe_id, timestamp)
                    )
                ''')

                # Create indexes for better query performance
                cur.execute('CREATE INDEX IF NOT EXISTS idx_measurements_timestamp ON measurements(timestamp DESC)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_probes_address ON probes(probe_address)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_sites_client ON sites(client_id)')

                # Insert default client and site if they don't exist
                cur.execute('''
                    INSERT INTO clients (name)
                    VALUES ('Default Client')
                    ON CONFLICT DO NOTHING
                    RETURNING id
                ''')
                client_id = cur.fetchone()
                if client_id:
                    client_id = client_id[0]
                else:
                    cur.execute("SELECT id FROM clients WHERE name = 'Default Client'")
                    client_id = cur.fetchone()[0]

                cur.execute('''
                    INSERT INTO sites (client_id, name)
                    VALUES (%s, 'Default Site')
                    ON CONFLICT DO NOTHING
                ''', (client_id,))

                self.conn.commit()
            except Exception as e:
                st.error(f"Error creating tables: {str(e)}")
                self.conn.rollback()
                raise

    def save_measurement(self, probe_data: Dict):
        try:
            with self.conn.cursor() as cur:
                # Get or create probe
                cur.execute('''
                    WITH default_site AS (
                        SELECT s.id FROM sites s
                        JOIN clients c ON s.client_id = c.id
                        WHERE c.name = 'Default Client' AND s.name = 'Default Site'
                        LIMIT 1
                    )
                    INSERT INTO probes (site_id, probe_address)
                    SELECT d.id, %s FROM default_site d
                    ON CONFLICT (probe_address) DO NOTHING
                    RETURNING id
                ''', (probe_data['address'],))

                probe_result = cur.fetchone()
                if probe_result:
                    probe_id = probe_result[0]
                else:
                    cur.execute('SELECT id FROM probes WHERE probe_address = %s', (probe_data['address'],))
                    probe_id = cur.fetchone()[0]

                # Insert measurement
                measurement_timestamp = datetime.strptime(probe_data['datetime'], '%Y-%m-%d %H:%M:%S')
                cur.execute('''
                    INSERT INTO measurements 
                    (probe_id, timestamp, status, product, water, density, discriminator, temperatures)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (probe_id, timestamp) DO NOTHING
                ''', (
                    probe_id,
                    measurement_timestamp,
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
                cur.execute('SELECT COUNT(*) as count FROM measurements')
                result = cur.fetchone()
                total_records = result['count'] if result else 0

                # Get paginated results
                cur.execute('''
                    SELECT 
                        m.timestamp,
                        p.probe_address,
                        m.status,
                        m.product,
                        m.water,
                        m.density,
                        m.discriminator
                    FROM measurements m
                    JOIN probes p ON m.probe_id = p.id
                    ORDER BY m.timestamp DESC
                    LIMIT %s OFFSET %s
                ''', (per_page, offset))
                records = cur.fetchall()

                return list(records), total_records
        except Exception as e:
            st.error(f"Error fetching measurement history: {str(e)}")
            return [], 0