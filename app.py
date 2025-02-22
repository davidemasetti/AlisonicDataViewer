import streamlit as st
from src.xml_parser import XMLParser
from src.data_validator import DataValidator
from src.ui_components import (
    render_header,
    render_upload_section,
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
    if 'last_upload_time' not in st.session_state:
        st.session_state.last_upload_time = None

    render_header()
    
    # File upload and refresh section
    uploaded_file, refresh_clicked = render_upload_section()

    if uploaded_file is not None:
        # Read and parse XML
        xml_content = uploaded_file.read().decode('utf-8')
        probe_data = XMLParser.parse_xml(xml_content)

        if probe_data is None:
            st.error("Error parsing XML file. Please check the file format.")
            return

        # Validate data
        is_valid, errors = DataValidator.validate_probe_data(probe_data)
        
        if not is_valid:
            render_error_messages(errors)
            return

        # Update last upload time
        st.session_state.last_upload_time = probe_data['datetime']

        # Render dashboard components
        render_probe_info(probe_data)
        render_measurements(probe_data)
        render_temperature_graph(probe_data['temperatures'])

    elif refresh_clicked and st.session_state.last_upload_time:
        st.info("Please upload a new XML file to refresh the data.")
    else:
        st.info("Please upload an XML file to view the probe data.")

if __name__ == "__main__":
    main()
