import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import pandas as pd

def render_header():
    st.title("Cloud Probe Solution Dashboard")
    st.markdown("---")

def render_probe_info(probe_data):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Probe Address", probe_data['address'])
        status_value = probe_data['status']
        status_color = 'normal' if status_value == '0' else 'off'
        st.metric("Status", status_value, delta=None, delta_color=status_color)

    with col2:
        st.metric("Customer ID", probe_data['customer_id'])
        discriminator_map = {'D': 'Diesel', 'P': 'Benzina', 'N': 'Non definito'}
        st.metric("Discriminator", discriminator_map.get(probe_data['discriminator'], 'Unknown'))

    with col3:
        st.metric("Last Update", probe_data['datetime'])

def render_measurements(probe_data):
    st.subheader("Measurements")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Product", f"{float(probe_data['product']):.2f}")
    with col2:
        st.metric("Water", f"{float(probe_data['water']):.2f}")
    with col3:
        st.metric("Density", f"{float(probe_data['density']):.2f}")

def render_temperature_graph(temperatures):
    st.subheader("Temperature Distribution")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(1, len(temperatures) + 1)),
        y=temperatures,
        mode='lines+markers',
        name='Temperature'
    ))

    fig.update_layout(
        xaxis_title="Sensor Position",
        yaxis_title="Temperature (°C)",
        height=400,
        margin=dict(l=20, r=20, t=20, b=20),
        hovermode='x'
    )

    st.plotly_chart(fig, use_container_width=True)

def render_measurement_history(records, total_records, page, per_page=200):
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