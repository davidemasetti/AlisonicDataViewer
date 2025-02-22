import streamlit as st
import time
from src.xml_parser import XMLParser
from src.data_validator import DataValidator
from src.ui_components import (
    render_header,
    render_probe_info,
    render_measurements,
    render_temperature_graph,
    render_error_messages
)

# Local XML file path
XML_FILE = "attached_assets/alisonic_probes.xml"

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

    render_header()

    # Parse XML from local file
    probe_data = XMLParser.parse_xml_file(XML_FILE)

    if probe_data is None:
        st.error("Error parsing XML data. Please check the data source.")
        time.sleep(1)
        st.rerun()
        return

    # Validate data
    is_valid, errors = DataValidator.validate_probe_data(probe_data)

    if not is_valid:
        render_error_messages(errors)
        time.sleep(1)
        st.rerun()
        return

    # Update last fetch time
    st.session_state.last_update_time = probe_data['datetime']

    # Render dashboard components
    render_probe_info(probe_data)
    render_measurements(probe_data)
    render_temperature_graph(probe_data['temperatures'])

    # Auto-refresh after 1 second
    time.sleep(1)
    st.rerun()

if __name__ == "__main__":
    main()