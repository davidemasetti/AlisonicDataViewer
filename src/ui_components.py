import streamlit as st
import pandas as pd
from datetime import datetime

def render_header():
    st.title("Cloud Probe Solution Dashboard")
    st.markdown("---")

def get_alarm_status_info(status: str) -> tuple[str, str]:
    try:
        status_int = int(status)
        if status_int == 0:
            return "OK", "normal"  # Changed from "green" to "normal"
        elif status_int == 1:
            return "Acknowledged", "inverse"  # Changed from "yellow" to "inverse"
        else:
            return "Alarm", "off"  # Changed from "red" to "off"
    except ValueError:
        return "Unknown", "off"  # Changed from "gray" to "off"

def render_probe_summary(probe_data_list, select_callback=None):
    st.subheader("Site Overview")

    # Create summary data
    summary_data = []
    for probe in probe_data_list:
        avg_temp = sum(probe['temperatures']) / len(probe['temperatures']) if probe['temperatures'] else 0
        summary_data.append({
            'Probe ID': probe['address'],
            'Ullage (mm)': f"{float(probe['ullage']):.2f}",
            'Product Volume (mm)': f"{float(probe['product']):.2f}",
            'Temperature (°C)': f"{avg_temp:.1f}",
            'Status': get_alarm_status_info(probe['alarm_status'])[0]
        })

    # Convert to DataFrame for better display
    if summary_data:
        df = pd.DataFrame(summary_data)
        
        # Use an interactive dataframe with row selection if callback is provided
        if select_callback:
            st.dataframe(
                df,
                use_container_width=True,
                column_config={
                    "Probe ID": st.column_config.TextColumn(
                        "Probe ID",
                        help="Unique identifier for the probe",
                        width="medium",
                    ),
                    "Status": st.column_config.TextColumn(
                        "Status",
                        width="small",
                    ),
                }
            )
            
            # Add action buttons for each probe
            cols = st.columns(len(summary_data))
            for i, (col, probe) in enumerate(zip(cols, probe_data_list)):
                with col:
                    if st.button(f"View Probe {probe['address']}", key=f"probe_button_{i}"):
                        select_callback(probe['address'])
        else:
            st.dataframe(df, use_container_width=True)
    else:
        st.info("No probe data available for this site.")

def render_probe_info(probe_data):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Probe Address", probe_data['address'])
        alarm_text, alarm_color = get_alarm_status_info(probe_data['alarm_status'])
        st.metric("Alarm Status", alarm_text, delta=" ", delta_color=alarm_color)
        st.metric("Probe Status", probe_data['probe_status'])
        st.metric("Tank Status", probe_data['tank_status'])

    with col2:
        st.metric("Customer ID", probe_data['customer_id'])
        st.metric("Site ID", probe_data['site_id'])
        discriminator_map = {'D': 'Diesel', 'P': 'Benzina', 'N': 'Non definito'}
        st.metric("Discriminator", discriminator_map.get(probe_data['discriminator'], 'Unknown'))

    with col3:
        st.metric("Last Update", probe_data['datetime'])
        st.metric("Ullage", f"{float(probe_data['ullage']):.2f} mm")

def render_measurements(probe_data):
    st.subheader("Measurements")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Product", f"{float(probe_data['product']):.2f} mm")
    with col2:
        st.metric("Water", f"{float(probe_data['water']):.2f} mm")
    with col3:
        st.metric("Density", f"{float(probe_data['density']):.2f} kg/m³")

def render_measurement_history(records, total_records, page: int = 1, per_page: int = 200):
    st.subheader("Measurement History")

    if not records:
        st.info("No historical data available yet.")
        return

    try:
        # Convert records to pandas DataFrame for better display
        df = pd.DataFrame(records)
        
        # Handle potential missing columns to avoid errors
        expected_columns = ['timestamp', 'probe_address', 'status', 'probe_status', 
                           'alarm_status', 'tank_status', 'product', 'water', 
                           'density', 'ullage', 'discriminator']
        
        for col in expected_columns:
            if col not in df.columns:
                df[col] = None
        
        # Format timestamp - handle possible null values
        if 'timestamp' in df.columns:
            # Replace NaN or None values with a placeholder
            df['timestamp'] = df['timestamp'].fillna('N/A')
            # Only format datetime values, not the placeholders
            mask = df['timestamp'] != 'N/A'
            if mask.any():
                df.loc[mask, 'timestamp'] = pd.to_datetime(df.loc[mask, 'timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        st.error(f"Error processing measurement data: {str(e)}")
        return

    # Reorder and rename columns
    columns = {
        'timestamp': 'Timestamp',
        'probe_address': 'Probe Address',
        'status': 'Status',  # Renamed to avoid duplication with probe_status
        'probe_status': 'Probe Status',
        'alarm_status': 'Alarm Status',
        'tank_status': 'Tank Status',
        'product': 'Product (mm)',
        'water': 'Water (mm)',
        'density': 'Density (kg/m³)',
        'ullage': 'Ullage (mm)',
        'discriminator': 'Discriminator'
    }
    
    # Filter out columns that don't exist in the dataframe
    available_columns = {k: v for k, v in columns.items() if k in df.columns}
    
    # Check for potential duplicate column names after renaming
    if len(set(available_columns.values())) < len(available_columns.values()):
        # There are duplicate column names, let's create a safe mapping
        used_names = set()
        safe_columns = {}
        for k, v in available_columns.items():
            if v in used_names:
                # Append a number to make unique
                count = 1
                while f"{v} ({count})" in used_names:
                    count += 1
                safe_columns[k] = f"{v} ({count})"
                used_names.add(f"{v} ({count})")
            else:
                safe_columns[k] = v
                used_names.add(v)
        available_columns = safe_columns
    
    # Apply column renaming
    df = df[list(available_columns.keys())].rename(columns=available_columns)

    # Display table with pagination info
    st.dataframe(df, use_container_width=True)

    # Pagination controls
    total_pages = (total_records + per_page - 1) // per_page

    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown(f"Page {page} of {total_pages} (Total records: {total_records})")

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if page > 1:
            if st.button("⏮️ First"):
                st.session_state.history_page = 1
                st.rerun()
    with col2:
        if page > 1:
            if st.button("◀️ Previous"):
                st.session_state.history_page = page - 1
                st.rerun()
    with col3:
        if page < total_pages:
            if st.button("Next ▶️"):
                st.session_state.history_page = page + 1
                st.rerun()
    with col4:
        if page < total_pages:
            if st.button("Last ⏭️"):
                st.session_state.history_page = total_pages
                st.rerun()

def render_error_messages(errors):
    for error in errors:
        st.error(error)