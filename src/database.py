import os
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from typing import List, Dict, Optional
import streamlit as st

class Database:
    def __init__(self):
        self.conn = None
        self.connect()

    def connect(self):
        """Establish database connection"""
        try:
            if self.conn is None or self.conn.closed:
                self.conn = psycopg2.connect(os.environ['DATABASE_URL'])
                self.create_tables()
        except Exception as e:
            st.error(f"Database connection error: {str(e)}")
            raise

    def ensure_connection(self):
        """Ensure database connection is active"""
        try:
            if self.conn is None or self.conn.closed:
                self.connect()
            # Test the connection
            with self.conn.cursor() as cur:
                cur.execute('SELECT 1')
        except Exception as e:
            st.error(f"Lost database connection, attempting to reconnect: {str(e)}")
            self.connect()

    def create_tables(self):
        with self.conn.cursor() as cur:
            try:
                # Create clients table
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS clients (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100) NOT NULL UNIQUE,
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
                        probe_status INTEGER NOT NULL DEFAULT 0,
                        alarm_status INTEGER NOT NULL DEFAULT 0,
                        tank_status INTEGER NOT NULL DEFAULT 0,
                        ullage DECIMAL(7,2) NOT NULL DEFAULT 0.0,
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
            self.ensure_connection()
            with self.conn.cursor() as cur:
                # Get or create client based on customer_id
                customer_id = probe_data['customer_id']
                cur.execute('''
                    INSERT INTO clients (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                    RETURNING id
                ''', (f"Customer {customer_id}",))

                client_result = cur.fetchone()
                if client_result:
                    client_id = client_result[0]
                else:
                    cur.execute('SELECT id FROM clients WHERE name = %s', (f"Customer {customer_id}",))
                    client_id = cur.fetchone()[0]

                # Get or create site based on site_id and client_id
                site_id = probe_data['site_id']
                cur.execute('''
                    INSERT INTO sites (client_id, name)
                    VALUES (%s, %s)
                    ON CONFLICT (client_id, name) DO NOTHING
                    RETURNING id
                ''', (client_id, f"Site {site_id}"))

                site_result = cur.fetchone()
                if site_result:
                    db_site_id = site_result[0]
                else:
                    cur.execute('SELECT id FROM sites WHERE client_id = %s AND name = %s', 
                                (client_id, f"Site {site_id}"))
                    db_site_id = cur.fetchone()[0]

                # Get or create probe
                cur.execute('''
                    INSERT INTO probes (site_id, probe_address)
                    VALUES (%s, %s)
                    ON CONFLICT (probe_address) DO NOTHING
                    RETURNING id
                ''', (db_site_id, probe_data['address']))

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
                    (probe_id, timestamp, status, product, water, density, discriminator, temperatures,
                     probe_status, alarm_status, tank_status, ullage)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (probe_id, timestamp) DO NOTHING
                ''', (
                    probe_id,
                    measurement_timestamp,
                    probe_data['probe_status'],
                    float(probe_data['product']),
                    float(probe_data['water']),
                    float(probe_data['density']),
                    probe_data['discriminator'],
                    json.dumps(probe_data['temperatures']),
                    int(probe_data['probe_status']),
                    int(probe_data['alarm_status']),
                    int(probe_data['tank_status']),
                    float(probe_data['ullage'])
                ))
                self.conn.commit()
        except Exception as e:
            st.error(f"Error saving measurement: {str(e)}")
            self.conn.rollback()
            raise

    def get_measurement_history(self, probe_id: str, page: int = 1, per_page: int = 200) -> tuple[List[Dict], int]:
        try:
            self.ensure_connection()
            offset = (page - 1) * per_page
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get total count for the specific probe
                cur.execute('''
                    SELECT COUNT(*) as count 
                    FROM measurements m
                    JOIN probes p ON m.probe_id = p.id
                    WHERE p.probe_address = %s
                ''', (probe_id,))
                result = cur.fetchone()
                total_records = result['count'] if result else 0

                # Get paginated results for the specific probe
                cur.execute('''
                    SELECT 
                        m.timestamp,
                        p.probe_address,
                        m.status,
                        m.product,
                        m.water,
                        m.density,
                        m.discriminator,
                        m.probe_status,
                        m.alarm_status,
                        m.tank_status,
                        m.ullage
                    FROM measurements m
                    JOIN probes p ON m.probe_id = p.id
                    WHERE p.probe_address = %s
                    ORDER BY m.timestamp DESC
                    LIMIT %s OFFSET %s
                ''', (probe_id, per_page, offset))
                records = cur.fetchall()

                return list(records), total_records
        except Exception as e:
            st.error(f"Error fetching measurement history: {str(e)}")
            return [], 0
            
    def get_all_clients(self):
        """Get all clients from the database"""
        try:
            self.ensure_connection()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT id, name 
                    FROM clients
                    ORDER BY name
                ''')
                return cur.fetchall()
        except Exception as e:
            st.error(f"Error fetching clients: {str(e)}")
            return []
            
    def get_sites_for_client(self, client_id):
        """Get all sites for a specific client"""
        try:
            self.ensure_connection()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT id, name 
                    FROM sites
                    WHERE client_id = %s
                    ORDER BY name
                ''', (client_id,))
                return cur.fetchall()
        except Exception as e:
            st.error(f"Error fetching sites: {str(e)}")
            return []
            
    def get_probes_for_site(self, site_id):
        """Get all probes for a specific site"""
        try:
            self.ensure_connection()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT id, probe_address 
                    FROM probes
                    WHERE site_id = %s
                    ORDER BY probe_address
                ''', (site_id,))
                return cur.fetchall()
        except Exception as e:
            st.error(f"Error fetching probes: {str(e)}")
            return []
    
    def get_latest_measurements_for_site(self, site_id):
        """Get the latest measurement for each probe in a site"""
        try:
            self.ensure_connection()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    WITH latest_measurements AS (
                        SELECT 
                            m.probe_id,
                            MAX(m.timestamp) as latest_timestamp
                        FROM 
                            measurements m
                            JOIN probes p ON m.probe_id = p.id
                            JOIN sites s ON p.site_id = s.id
                        WHERE 
                            s.id = %s
                        GROUP BY 
                            m.probe_id
                    )
                    SELECT 
                        p.probe_address,
                        m.timestamp,
                        m.product,
                        m.water,
                        m.density,
                        m.probe_status,
                        m.alarm_status,
                        m.tank_status,
                        m.ullage,
                        m.temperatures
                    FROM 
                        latest_measurements lm
                        JOIN measurements m ON lm.probe_id = m.probe_id AND lm.latest_timestamp = m.timestamp
                        JOIN probes p ON m.probe_id = p.id
                    ORDER BY 
                        p.probe_address
                ''', (site_id,))
                return cur.fetchall()
        except Exception as e:
            st.error(f"Error fetching latest measurements: {str(e)}")
            return []