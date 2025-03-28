import os
import psycopg2
import streamlit as st

def main():
    st.set_page_config(page_title="Database Optimization", page_icon="🔧", layout="wide")
    
    st.title("Database Optimization Tool")
    st.write("This tool creates additional indexes in the database to improve query performance for large datasets.")
    
    # Connect to the database
    try:
        conn = psycopg2.connect(os.environ['DATABASE_URL'])
        st.success("Successfully connected to the database")
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        return
    
    # Create optimization button
    if st.button("Optimize Database"):
        with st.spinner("Creating indexes..."):
            try:
                with conn.cursor() as cur:
                    # Create indexes for better query performance with high volume data
                    
                    # Index on measurements.probe_id for faster filtering by probe
                    cur.execute('CREATE INDEX IF NOT EXISTS idx_measurements_probe_id ON measurements(probe_id)')
                    
                    # Index on discriminator for filtering by fuel type
                    cur.execute('CREATE INDEX IF NOT EXISTS idx_measurements_discriminator ON measurements(discriminator)')
                    
                    # Composite index for probe_id + timestamp for faster history queries
                    cur.execute('CREATE INDEX IF NOT EXISTS idx_probe_timestamp ON measurements(probe_id, timestamp DESC)')
                    
                    # Index for faster range queries on product value
                    cur.execute('CREATE INDEX IF NOT EXISTS idx_measurements_product ON measurements(product)')
                    
                    # Index for faster range queries on water value 
                    cur.execute('CREATE INDEX IF NOT EXISTS idx_measurements_water ON measurements(water)')
                    
                    # Index for faster range queries on density
                    cur.execute('CREATE INDEX IF NOT EXISTS idx_measurements_density ON measurements(density)')
                    
                    # Index for clients.name for faster client lookup
                    cur.execute('CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name)')
                    
                    # Index for probes by site for faster site-based queries
                    cur.execute('CREATE INDEX IF NOT EXISTS idx_probes_site ON probes(site_id)')
                
                # Analyze tables to update statistics for query optimizer
                with conn.cursor() as cur:
                    cur.execute('ANALYZE clients')
                    cur.execute('ANALYZE sites')
                    cur.execute('ANALYZE probes')
                    cur.execute('ANALYZE measurements')
                
                conn.commit()
                st.success("Database optimization completed successfully!")
                
                # Show existing indexes
                with conn.cursor() as cur:
                    cur.execute("""
                    SELECT
                        tablename,
                        indexname,
                        indexdef
                    FROM
                        pg_indexes
                    WHERE
                        schemaname = 'public'
                    ORDER BY
                        tablename,
                        indexname;
                    """)
                    
                    results = cur.fetchall()
                    
                    if results:
                        st.subheader("Current Database Indexes")
                        
                        # Group indexes by table
                        tables = {}
                        for row in results:
                            table_name, index_name, index_def = row
                            if table_name not in tables:
                                tables[table_name] = []
                            tables[table_name].append((index_name, index_def))
                        
                        # Display indexes by table
                        for table_name, indexes in tables.items():
                            with st.expander(f"Table: {table_name}"):
                                for index_name, index_def in indexes:
                                    st.code(index_def)
                    else:
                        st.info("No indexes found.")
                
            except Exception as e:
                conn.rollback()
                st.error(f"Error creating indexes: {str(e)}")
            finally:
                conn.close()
    
    # Option to return to main dashboard
    st.markdown("---")
    if st.button("Return to Dashboard"):
        st.switch_page("app.py")

if __name__ == "__main__":
    main()