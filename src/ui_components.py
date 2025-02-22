import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

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

def render_error_messages(errors):
    for error in errors:
        st.error(error)