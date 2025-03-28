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
    "attached_assets/S1-C22-S12-20250227095512.XML",
    "attached_assets/alisonic_probes.xml"
]

# Initialize database connection using Streamlit's cache
@st.cache_resource
def get_database():
    try:
        return Database()
    except Exception as e:
        st.error(f"Failed to initialize database: {str(e)}")
        return None

def get_clients(db):
    """Get list of clients from database"""
    return db.get_clients()

def get_sites_for_client(db, client_id):
    """Get list of sites for a specific client"""
    return db.get_sites_for_client(client_id)

def get_probes_for_site(db, site_id):
    """Get list of probes for a specific site"""
    return db.get_probes_for_site(site_id)

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
    if 'selected_client_id' not in st.session_state:
        st.session_state.selected_client_id = None
    if 'selected_site_id' not in st.session_state:
        st.session_state.selected_site_id = None
    if 'selected_probe_id' not in st.session_state:
        st.session_state.selected_probe_id = None
    if 'show_probe_details' not in st.session_state:
        st.session_state.show_probe_details = False
    if 'xml_file_index' not in st.session_state:
        st.session_state.xml_file_index = 0
    
    render_header()

    # Initialize database connection
    db = get_database()
    if db is None:
        st.error("Could not connect to database. Please check your configuration.")
        return

    # Add refresh rate indicator in sidebar
    st.sidebar.markdown("### Auto-refresh Settings")
    refresh_rate = st.sidebar.slider("Refresh interval (seconds)", 
                                   min_value=1, 
                                   max_value=10, 
                                   value=1)
    
    # Setup the hierarchical navigation in sidebar
    st.sidebar.markdown("### Navigation")
    
    # Import XML data section
    st.sidebar.markdown("#### Import XML Data")
    
    # Add links to batch import tools
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Batch Import", use_container_width=True):
            st.switch_page("batch_import_xml.py")
    with col2:
        if st.button("High Volume Import", use_container_width=True):
            st.switch_page("high_volume_import.py")
            
    # Add link to database optimization tool
    if st.sidebar.button("Optimize Database", use_container_width=True):
        st.switch_page("optimize_database.py")
    
    # For development/demo: Add XML file selector in sidebar
    selected_xml = st.sidebar.selectbox(
        "Quick Import Single File",
        XML_FILES,
        index=st.session_state.xml_file_index,
        format_func=lambda x: f"Site {os.path.basename(x).split('.')[0]}"
    )
    st.session_state.xml_file_index = XML_FILES.index(selected_xml)
    
    # Parse and save XML data from selected file
    if st.sidebar.button("Import Data"):
        probe_data_list = XMLParser.parse_xml_file(selected_xml)
        
        if probe_data_list and len(probe_data_list) > 0:
            imported_count = 0
            for probe_data in probe_data_list:
                # Validate each probe's data
                is_valid, errors = DataValidator.validate_probe_data(probe_data)
                if is_valid:
                    try:
                        # Check if measurement already exists
                        if not db.measurement_exists(probe_data['address'], probe_data['datetime']):
                            db.save_measurement(probe_data)
                            imported_count += 1
                    except Exception as e:
                        st.sidebar.error(f"Error saving data: {str(e)}")
            
            if imported_count > 0:
                st.sidebar.success(f"Imported {imported_count} new measurements")
            else:
                st.sidebar.info("No new measurements to import")
        else:
            st.sidebar.error("Failed to parse XML data")
    
    # Client selection
    st.sidebar.markdown("#### Client Selection")
    clients = get_clients(db)
    client_options = [f"Client {client['id']} - {client['name']}" for client in clients]
    
    if not clients:
        st.sidebar.warning("No clients available. Import data first.")
    else:
        selected_client_option = st.sidebar.selectbox(
            "Select Client",
            client_options,
            index=0
        )
        # Extract client_id from the selected option
        selected_client_id = int(selected_client_option.split(' - ')[0].replace('Client ', ''))
        st.session_state.selected_client_id = selected_client_id
        
        # Site selection
        st.sidebar.markdown("#### Site Selection")
        sites = get_sites_for_client(db, selected_client_id)
        
        if not sites:
            st.sidebar.warning(f"No sites available for Client {selected_client_id}")
        else:
            site_options = [f"Site {site['id']} - {site['name']}" for site in sites]
            selected_site_option = st.sidebar.selectbox(
                "Select Site",
                site_options,
                index=0
            )
            # Extract site_id from the selected option
            selected_site_id = int(selected_site_option.split(' - ')[0].replace('Site ', ''))
            st.session_state.selected_site_id = selected_site_id
            
            # Load all probes for the selected site
            probes = get_probes_for_site(db, selected_site_id)
            
            if not probes:
                st.warning(f"No probes available for Site {selected_site_id}")
                return
                
            # Get the latest measurement for all probes to display in summary
            probe_data_list = []
            for probe in probes:
                latest_measurement = db.get_latest_measurement(probe['probe_address'])
                if latest_measurement:
                    probe_data_list.append(latest_measurement)
            
            if not probe_data_list:
                st.warning("No measurement data available. Please import data first.")
                return
                
            # Probe selection in sidebar (only shown in detailed view)
            if st.session_state.show_probe_details:
                st.sidebar.markdown("#### Probe Selection")
                probe_options = [f"Probe {probe['probe_address']}" for probe in probes]
                
                selected_probe_option = st.sidebar.selectbox(
                    "Select Probe",
                    probe_options,
                    index=0
                )
                # Extract probe_address from the selected option
                selected_probe_address = selected_probe_option.replace('Probe ', '')
                st.session_state.selected_probe_id = selected_probe_address
                
                # Get the selected probe data
                selected_probe_data = next((data for data in probe_data_list if data['probe_address'] == selected_probe_address), None)
                
                if not selected_probe_data:
                    st.error(f"No measurement data available for probe {selected_probe_address}")
                    return
                
                # Render detailed probe view
                if st.button("Back to Summary"):
                    st.session_state.show_probe_details = False
                    st.rerun()
                
                render_probe_info(selected_probe_data)
                render_measurements(selected_probe_data)
                
                # Fetch and display measurement history for selected probe
                records, total_records = db.get_measurement_history(
                    probe_id=selected_probe_address,
                    page=st.session_state.history_page,
                    per_page=200
                )
                render_measurement_history(records, total_records, st.session_state.history_page)
            else:
                # Render summary dashboard with all probes
                render_probe_summary(probe_data_list)
                
                # Create buttons for each probe to view details
                cols = st.columns(min(len(probe_data_list), 4))  # Up to 4 columns
                for i, probe_data in enumerate(probe_data_list):
                    with cols[i % 4]:
                        if st.button(f"View Details for {probe_data['probe_address']}"):
                            st.session_state.show_probe_details = True
                            st.session_state.selected_probe_id = probe_data['probe_address']
                            st.rerun()

    # Display last update time
    st.sidebar.markdown("### Status")
    st.sidebar.text(f"Last update: {st.session_state.last_update_time or 'Never'}")

    # Auto-refresh using Streamlit's native rerun
    time.sleep(refresh_rate)
    st.rerun()

if __name__ == "__main__":
    main()