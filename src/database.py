import os
import time
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from typing import List, Dict, Optional, Tuple
import streamlit as st

class Database:
    def __init__(self):
        self.conn = None
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                self.connect()
                # If we get here, connection was successful
                break
            except Exception as e:
                st.error(f"Database connection attempt {attempt+1}/{max_attempts} failed: {str(e)}")
                if attempt < max_attempts - 1:
                    # Wait before retrying
                    time.sleep(1)
                else:
                    # Last attempt failed
                    raise

    def connect(self):
        """Establish database connection"""
        try:
            # Always close the old connection if it exists
            if hasattr(self, 'conn') and self.conn is not None:
                try:
                    self.conn.close()
                except:
                    pass  # Ignore errors on closing
                
            # Create a fresh connection
            self.conn = psycopg2.connect(os.environ['DATABASE_URL'])
            self.conn.autocommit = False  # Explicitly manage transactions
            
            # Initialize the database schema
            self.create_tables()
            return True
        except Exception as e:
            if hasattr(self, 'conn') and self.conn is not None:
                try:
                    self.conn.close()
                except:
                    pass
            self.conn = None
            st.error(f"Database connection error: {str(e)}")
            raise

    def ensure_connection(self):
        """Ensure database connection is active"""
        if self.conn is None or self.conn.closed:
            return self.connect()
            
        # Test the connection
        try:
            with self.conn.cursor() as cur:
                cur.execute('SELECT 1')
                cur.fetchone()
            return True
        except Exception:
            # Connection is broken, create a new one
            return self.connect()

    def create_tables(self):
        """Create database schema if it doesn't exist"""
        try:
            with self.conn.cursor() as cur:
                # Create tables if they don't exist
                
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
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for better query performance
                cur.execute('CREATE INDEX IF NOT EXISTS idx_measurements_timestamp ON measurements(timestamp DESC)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_measurements_probe_timestamp ON measurements(probe_id, timestamp)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_probes_address ON probes(probe_address)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_sites_client ON sites(client_id)')

                # Insert default client and site if they don't exist
                cur.execute('''
                    INSERT INTO clients (name)
                    VALUES ('Default Client')
                    ON CONFLICT (name) DO NOTHING
                    RETURNING id
                ''')
                result = cur.fetchone()
                if result:
                    client_id = result[0]
                else:
                    # Get the ID if the client already exists
                    cur.execute("SELECT id FROM clients WHERE name = 'Default Client'")
                    result = cur.fetchone()
                    client_id = result[0] if result else None
                
                if client_id:
                    cur.execute('''
                        INSERT INTO sites (client_id, name)
                        VALUES (%s, 'Default Site')
                        ON CONFLICT (client_id, name) DO NOTHING
                    ''', (client_id,))

                self.conn.commit()
                return True
            
        except Exception as e:
            self.conn.rollback()
            st.error(f"Error creating tables: {str(e)}")
            raise

    def save_measurement(self, probe_data: Dict):
        """Save a measurement to the database"""
        try:
            self.ensure_connection()
            with self.conn.cursor() as cur:
                # Get or create client based on customer_id
                customer_id = probe_data.get('customer_id', '0')
                customer_name = f"Customer {customer_id}"
                
                cur.execute('''
                    INSERT INTO clients (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                    RETURNING id
                ''', (customer_name,))
                
                result = cur.fetchone()
                if result:
                    client_id = result[0]
                else:
                    cur.execute('SELECT id FROM clients WHERE name = %s', (customer_name,))
                    result = cur.fetchone()
                    client_id = result[0] if result else None

                if not client_id:
                    raise Exception(f"Failed to get or create client: {customer_name}")

                # Get or create site based on site_id and client_id
                site_id = probe_data.get('site_id', '0')
                site_name = f"Site {site_id}"
                
                cur.execute('''
                    INSERT INTO sites (client_id, name)
                    VALUES (%s, %s)
                    ON CONFLICT (client_id, name) DO NOTHING
                    RETURNING id
                ''', (client_id, site_name))
                
                result = cur.fetchone()
                if result:
                    db_site_id = result[0]
                else:
                    cur.execute('SELECT id FROM sites WHERE client_id = %s AND name = %s', 
                               (client_id, site_name))
                    result = cur.fetchone()
                    db_site_id = result[0] if result else None
                
                if not db_site_id:
                    raise Exception(f"Failed to get or create site: {site_name}")

                # Get or create probe
                probe_address = probe_data.get('address', '')
                if not probe_address:
                    raise Exception("Missing probe address in data")
                    
                cur.execute('''
                    INSERT INTO probes (site_id, probe_address)
                    VALUES (%s, %s)
                    ON CONFLICT (probe_address) DO NOTHING
                    RETURNING id
                ''', (db_site_id, probe_address))
                
                result = cur.fetchone()
                if result:
                    probe_id = result[0]
                else:
                    cur.execute('SELECT id FROM probes WHERE probe_address = %s', (probe_address,))
                    result = cur.fetchone()
                    probe_id = result[0] if result else None
                
                if not probe_id:
                    raise Exception(f"Failed to get or create probe: {probe_address}")

                # Process timestamp
                datetime_str = probe_data.get('datetime', '')
                if not datetime_str:
                    raise Exception("Missing datetime in probe data")
                    
                try:
                    measurement_timestamp = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        # Try with dots between time components
                        alt_datetime_str = datetime_str.replace('.', ':')
                        measurement_timestamp = datetime.strptime(alt_datetime_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError as e:
                        raise Exception(f"Invalid datetime format: {datetime_str}. Error: {str(e)}")

                # Check if measurement already exists
                cur.execute('''
                    SELECT id FROM measurements 
                    WHERE probe_id = %s AND timestamp = %s
                ''', (probe_id, measurement_timestamp))
                
                existing_measurement = cur.fetchone()
                
                if existing_measurement:
                    # Skip if the measurement already exists
                    self.conn.commit()
                    return
                
                # Default values for missing fields
                probe_status = probe_data.get('probe_status', probe_data.get('status', 0))
                if probe_status == '':
                    probe_status = 0
                    
                alarm_status = probe_data.get('alarm_status', 0)
                if alarm_status == '':
                    alarm_status = 0
                    
                tank_status = probe_data.get('tank_status', 0)
                if tank_status == '':
                    tank_status = 0
                    
                ullage = probe_data.get('ullage', 0.0)
                if ullage == '':
                    ullage = 0.0
                
                # Make sure discriminator is never null or empty
                discriminator = probe_data.get('discriminator')
                if discriminator is None or discriminator == '':
                    discriminator = 'N'
                
                # Insert the measurement
                try:
                    cur.execute('''
                        INSERT INTO measurements 
                        (probe_id, timestamp, status, product, water, density, discriminator, 
                         temperatures, probe_status, alarm_status, tank_status, ullage)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (
                        probe_id,
                        measurement_timestamp,
                        str(probe_status),
                        float(probe_data.get('product', 0)),
                        float(probe_data.get('water', 0)),
                        float(probe_data.get('density', 0)),
                        discriminator,
                        json.dumps(probe_data.get('temperatures', [])),
                        int(probe_status),
                        int(alarm_status),
                        int(tank_status),
                        float(ullage)
                    ))
                    self.conn.commit()
                except Exception as e:
                    self.conn.rollback()
                    raise Exception(f"Failed to insert measurement: {str(e)}")
                    
        except Exception as e:
            try:
                self.conn.rollback()
            except:
                pass
            st.error(f"Error saving measurement: {str(e)}")
            # Don't raise the exception here to avoid breaking the app flow

    def get_measurement_history(self, probe_id: str, page: int = 1, per_page: int = 200) -> Tuple[List[Dict], int]:
        """Get measurement history for a probe"""
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