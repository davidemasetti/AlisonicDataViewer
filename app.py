import streamlit as st
import time
from src.xml_parser import XMLParser
from src.data_validator import DataValidator
from src.ui_components import (
    render_header,
    render_url_input,
    render_probe_info,
    render_measurements,
    render_temperature_graph,
    render_error_messages
)

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

    # URL input section
    url = render_url_input()

    if url:
        # Fetch and parse XML
        probe_data = XMLParser.fetch_and_parse_xml(url)

        if probe_data is None:
            st.error("Error fetching or parsing XML data. Please check the URL and data format.")
            return

        # Validate data
        is_valid, errors = DataValidator.validate_probe_data(probe_data)

        if not is_valid:
            render_error_messages(errors)
            return

        # Update last fetch time
        st.session_state.last_update_time = probe_data['datetime']

        # Render dashboard components
        render_probe_info(probe_data)
        render_measurements(probe_data)
        render_temperature_graph(probe_data['temperatures'])

        # Add auto-refresh
        time.sleep(1)  # Wait for 1 second
        st.rerun()  # Rerun the app to fetch new data
    else:
        st.info("Please enter the URL of your XML data source.")

if __name__ == "__main__":
    main()