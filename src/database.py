import os
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
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
                # Get or create client
                customer_id = probe_data.get('customer_id', '')
                client_name = f"Customer {customer_id}"
                
                cur.execute('''
                    INSERT INTO clients (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                    RETURNING id
                ''', (client_name,))
                
                client_result = cur.fetchone()
                if client_result:
                    client_id = client_result[0]
                else:
                    cur.execute('SELECT id FROM clients WHERE name = %s', (client_name,))
                    client_id = cur.fetchone()[0]
                
                # Get or create site
                site_id = probe_data.get('site_id', '')
                site_name = f"Site {site_id}"
                
                cur.execute('''
                    INSERT INTO sites (client_id, name)
                    VALUES (%s, %s)
                    ON CONFLICT (client_id, name) DO NOTHING
                    RETURNING id
                ''', (client_id, site_name))
                
                site_result = cur.fetchone()
                if site_result:
                    site_id_db = site_result[0]
                else:
                    cur.execute('SELECT id FROM sites WHERE client_id = %s AND name = %s', 
                               (client_id, site_name))
                    site_id_db = cur.fetchone()[0]
                
                # Get or create probe
                cur.execute('''
                    INSERT INTO probes (site_id, probe_address)
                    VALUES (%s, %s)
                    ON CONFLICT (probe_address) DO NOTHING
                    RETURNING id
                ''', (site_id_db, probe_data['address']))

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
                    probe_data['probe_status'],
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

    def get_clients(self) -> List[Dict]:
        """
        Get all clients from the database
        
        Returns:
            List[Dict]: List of client dictionaries with id and name
        """
        try:
            self.ensure_connection()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('SELECT id, name FROM clients ORDER BY name')
                return cur.fetchall()
        except Exception as e:
            st.error(f"Error fetching clients: {str(e)}")
            return []
    
    def get_sites_for_client(self, client_id: int) -> List[Dict]:
        """
        Get all sites for a specific client
        
        Args:
            client_id (int): Client ID
            
        Returns:
            List[Dict]: List of site dictionaries with id and name
        """
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
            st.error(f"Error fetching sites for client {client_id}: {str(e)}")
            return []
    
    def get_probes_for_site(self, site_id: int) -> List[Dict]:
        """
        Get all probes for a specific site
        
        Args:
            site_id (int): Site ID
            
        Returns:
            List[Dict]: List of probe dictionaries with id and probe_address
        """
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
            st.error(f"Error fetching probes for site {site_id}: {str(e)}")
            return []
    
    def get_latest_measurement(self, probe_address: str) -> Optional[Dict]:
        """
        Get the latest measurement for a specific probe
        
        Args:
            probe_address (str): Probe address
            
        Returns:
            Optional[Dict]: Measurement data or None if no measurements exist
        """
        try:
            self.ensure_connection()
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute('''
                    SELECT 
                        p.probe_address,
                        c.id as client_id,
                        c.name as client_name,
                        s.id as site_id,
                        s.name as site_name,
                        m.timestamp as datetime,
                        m.status as probe_status,
                        '0' as alarm_status,
                        '0' as tank_status,
                        m.product,
                        m.water,
                        m.density,
                        m.discriminator,
                        m.temperatures
                    FROM measurements m
                    JOIN probes p ON m.probe_id = p.id
                    JOIN sites s ON p.site_id = s.id
                    JOIN clients c ON s.client_id = c.id
                    WHERE p.probe_address = %s
                    ORDER BY m.timestamp DESC
                    LIMIT 1
                ''', (probe_address,))
                
                result = cur.fetchone()
                if result:
                    # Convert to compatible format with XML parser output
                    # Unpack JSON data
                    if isinstance(result['temperatures'], str):
                        result['temperatures'] = json.loads(result['temperatures'])
                    
                    # Add address key for compatibility
                    result['address'] = result['probe_address']
                    
                    # Format datetime
                    if isinstance(result['datetime'], datetime):
                        result['datetime'] = result['datetime'].strftime('%Y-%m-%d %H:%M:%S')
                        
                    return result
                    
                return None
        except Exception as e:
            st.error(f"Error fetching latest measurement for probe {probe_address}: {str(e)}")
            return None
    
    def measurement_exists(self, probe_address: str, timestamp: str) -> bool:
        """
        Check if a measurement already exists for a specific probe and timestamp
        
        Args:
            probe_address (str): Probe address
            timestamp (str): Timestamp in 'YYYY-MM-DD HH:MM:SS' format
            
        Returns:
            bool: True if measurement exists, False otherwise
        """
        try:
            self.ensure_connection()
            with self.conn.cursor() as cur:
                cur.execute('''
                    SELECT 1
                    FROM measurements m
                    JOIN probes p ON m.probe_id = p.id
                    WHERE p.probe_address = %s
                    AND m.timestamp = %s
                    LIMIT 1
                ''', (probe_address, datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')))
                
                return cur.fetchone() is not None
        except Exception as e:
            st.error(f"Error checking if measurement exists: {str(e)}")
            return False
            
    def get_measurement_history(self, probe_id: str, page: int = 1, per_page: int = 200) -> Tuple[List[Dict], int]:
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
                
                # Log the total count for debugging
                print(f"Total records for probe {probe_id}: {total_records}")

                # Get paginated results for the specific probe with the fields that exist in the table
                cur.execute('''
                    SELECT 
                        m.timestamp,
                        p.probe_address,
                        m.status,
                        m.product,
                        m.water,
                        m.density,
                        m.discriminator,
                        m.temperatures
                    FROM measurements m
                    JOIN probes p ON m.probe_id = p.id
                    WHERE p.probe_address = %s
                    ORDER BY m.timestamp DESC
                    LIMIT %s OFFSET %s
                ''', (probe_id, per_page, offset))
                records = cur.fetchall()
                
                # Convert decimal values to floats for better JSON serialization
                for record in records:
                    for key, value in record.items():
                        if isinstance(value, Decimal):
                            record[key] = float(value)

                return list(records), total_records
        except Exception as e:
            st.error(f"Error fetching measurement history: {str(e)}")
            return [], 0