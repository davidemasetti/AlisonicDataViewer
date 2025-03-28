import streamlit as st
import time
import os
from src.xml_parser import XMLParser
from src.data_validator import DataValidator
from src.database import Database
from src.ui_components import (
    render_header,
    render_probe_info,
    render_measurements,
    render_measurement_history,
    render_error_messages,
    render_probe_summary
)

# XML file paths
XML_FILES = [
    "attached_assets/S1-C435-S1531-20250227095734.XML",
    "attached_assets/S1-C22-S12-20250227095512.XML"
]

# Additional timestamp files
TIMESTAMP_FILES = []
for file in os.listdir("attached_assets"):
    if file.lower().endswith(".xml") and " - " in file:
        TIMESTAMP_FILES.append(os.path.join("attached_assets", file))

# Add the alisonic_probes.xml file which contains probe 012345
ALISONIC_FILE = "attached_assets/alisonic_probes.xml"
if os.path.exists(ALISONIC_FILE):
    XML_FILES.append(ALISONIC_FILE)

# Initialize database connection using Streamlit's cache
@st.cache_resource(ttl=300)  # Cache expires after 5 minutes to refresh connection
def get_database():
    try:
        # Set up a new database connection
        db = Database()
        return db
    except Exception as e:
        st.error(f"Failed to initialize database: {str(e)}")
        return None

def select_probe_callback(probe_address):
    """Callback for when a probe is selected from the summary view"""
    probe_addresses = [probe['address'] for probe in st.session_state.probe_data_list]
    if probe_address in probe_addresses:
        st.session_state.selected_probe_index = probe_addresses.index(probe_address)
        st.session_state.show_probe_details = True
        st.rerun()

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
    if 'show_probe_details' not in st.session_state:
        st.session_state.show_probe_details = False
    if 'probe_data_list' not in st.session_state:
        st.session_state.probe_data_list = []

    render_header()

    # Initialize database connection
    db = get_database()
    if db is None:
        st.error("Could not connect to database. Please check your configuration.")
        return

    # Add sidebar content
    with st.sidebar:
        st.markdown("### Auto-refresh Settings")
        refresh_rate = st.slider("Refresh interval (seconds)", 
                               min_value=1, 
                               max_value=10, 
                               value=3)
                               
        st.markdown("### Site Selection")
        def format_site_name(path):
            filename = path.split('/')[-1]
            if "alisonic" in path.lower():
                return "Site alisonic_probes (012345)"
            elif "-" in filename:
                # For S1-C435-S1531-XXXXXXXX.XML format
                parts = filename.split('-')
                if len(parts) >= 3:
                    return f"Site {parts[1]}-{parts[2]}"
                else:
                    return filename
            else:
                return filename

        selected_xml = st.selectbox(
            "Select Site XML",
            XML_FILES,
            index=min(st.session_state.selected_xml_index, len(XML_FILES)-1),
            format_func=format_site_name
        )
        st.session_state.selected_xml_index = XML_FILES.index(selected_xml)
        
        # Import timestamp files in the background without UI controls
        if TIMESTAMP_FILES and 'timestamp_files_imported' not in st.session_state:
            with st.spinner("Importing timestamp data..."):
                for file_path in TIMESTAMP_FILES:
                    probe_data_list = XMLParser.parse_xml_file(file_path)
                    if probe_data_list:
                        for probe_data in probe_data_list:
                            is_valid, _ = DataValidator.validate_probe_data(probe_data)
                            if is_valid:
                                try:
                                    db.save_measurement(probe_data)
                                except Exception as e:
                                    # Silently handle import errors
                                    pass
                st.session_state.timestamp_files_imported = True
    
    # Parse XML from selected file
    probe_data_list = XMLParser.parse_xml_file(selected_xml)
    st.session_state.probe_data_list = probe_data_list

    if probe_data_list is None or len(probe_data_list) == 0:
        st.error("Error parsing XML data. Please check the data source.")
        time.sleep(1)
        st.rerun()
        return

    # Add probe selector to sidebar
    with st.sidebar:
        st.markdown("### Probe Selection")
        probe_addresses = [probe['address'] for probe in probe_data_list]
        selected_probe = st.selectbox(
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
    if db is not None:
        try:
            db.save_measurement(probe_data)
        except Exception as e:
            st.warning(f"Note: {str(e)}")
            # Continue with the application even if saving fails

    # Show either summary or detailed view
    if not st.session_state.show_probe_details:
        # Render summary dashboard
        render_probe_summary(probe_data_list, select_probe_callback)
    else:
        # Render detailed probe view
        if st.button("Back to Summary"):
            st.session_state.show_probe_details = False
            st.rerun()

        render_probe_info(probe_data)
        render_measurements(probe_data)

        # Fetch and display measurement history for selected probe
        try:
            if db is not None:
                records, total_records = db.get_measurement_history(
                    probe_id=selected_probe,
                    page=st.session_state.history_page,
                    per_page=10
                )
                render_measurement_history(records, total_records, st.session_state.history_page)
            else:
                st.warning("Database connection is not available. Unable to show measurement history.")
        except Exception as e:
            st.warning(f"Could not retrieve measurement history: {str(e)}")

    # Display last update time
    with st.sidebar:
        st.markdown("### Status")
        st.text(f"Last update: {st.session_state.last_update_time}")

    # Auto-refresh using Streamlit's native rerun
    time.sleep(refresh_rate)
    st.rerun()

if __name__ == "__main__":
    main()