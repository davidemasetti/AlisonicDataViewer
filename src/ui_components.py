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

def render_probe_summary(probe_data_list):
    st.subheader("Site Overview")

    # Create summary data
    summary_data = []
    for probe in probe_data_list:
        avg_temp = sum(probe['temperatures']) / len(probe['temperatures']) if probe['temperatures'] else 0
        
        # Use get() method with default value for optional fields
        # This prevents KeyError if a field is missing
        summary_data.append({
            'Probe ID': probe['address'],
            'Ullage (mm)': f"{float(probe.get('ullage', 0)):.2f}",
            'Product Volume (mm)': f"{float(probe['product']):.2f}",
            'Temperature (°C)': f"{avg_temp:.1f}",
            'Status': get_alarm_status_info(probe.get('alarm_status', '0'))[0]
        })

    # Convert to DataFrame for better display
    if summary_data:
        df = pd.DataFrame(summary_data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No probe data available for this site.")

def render_probe_info(probe_data):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Probe Address", probe_data['address'])
        alarm_text, alarm_color = get_alarm_status_info(probe_data.get('alarm_status', '0'))
        st.metric("Alarm Status", alarm_text, delta=None, delta_color=alarm_color)
        st.metric("Probe Status", probe_data.get('probe_status', '0'))
        st.metric("Tank Status", probe_data.get('tank_status', '0'))

    with col2:
        st.metric("Customer ID", probe_data.get('customer_id', 'N/A'))
        st.metric("Site ID", probe_data.get('site_id', 'N/A'))
        discriminator_map = {'D': 'Diesel', 'P': 'Benzina', 'N': 'Non definito'}
        st.metric("Discriminator", discriminator_map.get(probe_data['discriminator'], 'Unknown'))

    with col3:
        st.metric("Last Update", probe_data['datetime'])
        
        # Get ullage value, default to 0 if not present
        ullage_value = probe_data.get('ullage', '0')
        st.metric("Ullage", f"{float(ullage_value):.2f} mm")

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

    # Convert records to pandas DataFrame for better display
    df = pd.DataFrame(records)

    # Format timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

    # Reorder and rename columns
    columns = {
        'timestamp': 'Timestamp',
        'probe_address': 'Probe Address',
        'status': 'Status',
        'product': 'Product',
        'water': 'Water',
        'density': 'Density',
        'discriminator': 'Discriminator'
    }
    df = df[columns.keys()].rename(columns=columns)

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