import streamlit as st
import time
from src.xml_parser import XMLParser
from src.data_validator import DataValidator
from src.database import Database
from src.ui_components import (
    render_header,
    render_probe_info,
    render_measurements,
    render_temperature_graph,
    render_measurement_history,
    render_error_messages
)

# XML file paths
XML_FILES = [
    "attached_assets/S1-C435-S1531-20250227095734.XML",
    "attached_assets/S1-C22-S12-20250227095512.XML"
]

# Initialize database connection using Streamlit's cache
@st.cache_resource
def get_database():
    try:
        return Database()
    except Exception as e:
        st.error(f"Failed to initialize database: {str(e)}")
        return None

def main():
    # Page config
    st.set_page_config(
        page_title="Cloud Probe Solution",
        page_icon="📊",
        layout="wide"
    )

    # Initialize session state
    if 'last_update_time' not in st.session_state:
        st.session_state.last_update_time = None
    if 'history_page' not in st.session_state:
        st.session_state.history_page = 1
    if 'selected_probe_index' not in st.session_state:
        st.session_state.selected_probe_index = 0
    if 'selected_xml_index' not in st.session_state:
        st.session_state.selected_xml_index = 0

    render_header()

    # Add refresh rate indicator in sidebar
    st.sidebar.markdown("### Auto-refresh Settings")
    refresh_rate = st.sidebar.slider("Refresh interval (seconds)", 
                                   min_value=1, 
                                   max_value=10, 
                                   value=1)

    # Initialize database connection
    db = get_database()
    if db is None:
        st.error("Could not connect to database. Please check your configuration.")
        return

    # XML file selector in sidebar
    st.sidebar.markdown("### Site Selection")
    selected_xml = st.sidebar.selectbox(
        "Select Site XML",
        XML_FILES,
        index=st.session_state.selected_xml_index,
        format_func=lambda x: f"Site {x.split('/')[-1].split('.')[0]}"
    )
    st.session_state.selected_xml_index = XML_FILES.index(selected_xml)

    # Parse XML from selected file
    probe_data_list = XMLParser.parse_xml_file(selected_xml)

    if probe_data_list is None or len(probe_data_list) == 0:
        st.error("Error parsing XML data. Please check the data source.")
        time.sleep(1)
        st.rerun()
        return

    # Add probe selector to sidebar
    st.sidebar.markdown("### Probe Selection")
    probe_addresses = [probe['address'] for probe in probe_data_list]
    selected_probe = st.sidebar.selectbox(
        "Select Probe",
        probe_addresses,
        index=st.session_state.selected_probe_index
    )
    st.session_state.selected_probe_index = probe_addresses.index(selected_probe)

    # Get the selected probe data
    probe_data = probe_data_list[st.session_state.selected_probe_index]

    # Validate data
    is_valid, errors = DataValidator.validate_probe_data(probe_data)

    if not is_valid:
        render_error_messages(errors)
        time.sleep(1)
        st.rerun()
        return

    # Update last fetch time
    st.session_state.last_update_time = probe_data['datetime']

    # Save measurement to database
    try:
        db.save_measurement(probe_data)
    except Exception as e:
        st.error(f"Failed to save measurement: {str(e)}")

    # Render dashboard components
    render_probe_info(probe_data)
    render_measurements(probe_data)
    render_temperature_graph(probe_data['temperatures'])

    # Fetch and display measurement history
    records, total_records = db.get_measurement_history(
        page=st.session_state.history_page,
        per_page=200
    )
    render_measurement_history(records, total_records, st.session_state.history_page)

    # Display last update time
    st.sidebar.markdown("### Status")
    st.sidebar.text(f"Last update: {st.session_state.last_update_time}")

    # Auto-refresh using Streamlit's native rerun
    time.sleep(refresh_rate)
    st.rerun()

if __name__ == "__main__":
    main()