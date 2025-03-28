import os
import streamlit as st
import glob
from datetime import datetime
from src.xml_parser import XMLParser
from src.data_validator import DataValidator
from src.database import Database

def process_xml_file(db: Database, file_path: str) -> int:
    """
    Process a single XML file and save measurements to database
    
    Args:
        db: Database instance
        file_path: Path to XML file
        
    Returns:
        int: Number of new measurements imported
    """
    st.write(f"Processing file: {os.path.basename(file_path)}")
    
    # Parse XML data
    probe_data_list = XMLParser.parse_xml_file(file_path)
    
    if not probe_data_list:
        st.error(f"Failed to parse file: {os.path.basename(file_path)}")
        return 0
    
    # Count new measurements
    imported_count = 0
    
    # Process each probe in the file
    for probe_data in probe_data_list:
        # Validate probe data
        is_valid, errors = DataValidator.validate_probe_data(probe_data)
        
        if not is_valid:
            error_messages = "\n".join([f"- {err}" for err in errors])
            st.error(f"Invalid data for probe {probe_data.get('address', 'unknown')}:\n{error_messages}")
            continue
        
        try:
            # Check if measurement already exists
            if not db.measurement_exists(probe_data['address'], probe_data['datetime']):
                # Save to database
                db.save_measurement(probe_data)
                imported_count += 1
        except Exception as e:
            st.error(f"Error saving measurement for probe {probe_data.get('address', 'unknown')}: {str(e)}")
    
    return imported_count

def main():
    st.set_page_config(page_title="Batch XML Import", page_icon="📊", layout="wide")
    
    st.title("Batch XML Import Tool")
    st.write("This tool allows you to import multiple XML files at once.")
    
    # Initialize database
    try:
        db = Database()
    except Exception as e:
        st.error(f"Failed to connect to database: {str(e)}")
        return
    
    # UI for selecting files
    st.header("1. Select XML Files")
    
    # Option 1: Use a specific directory
    xml_dir = st.text_input("XML Directory Path", value="attached_assets", 
                           help="Enter the directory path containing XML files")
    
    # Find all XML files in the directory
    if xml_dir and os.path.isdir(xml_dir):
        xml_files = glob.glob(os.path.join(xml_dir, "*.XML")) + glob.glob(os.path.join(xml_dir, "*.xml"))
        
        if not xml_files:
            st.warning(f"No XML files found in directory: {xml_dir}")
        else:
            st.success(f"Found {len(xml_files)} XML files")
            
            # Display file list
            st.subheader("Available XML Files:")
            file_options = {os.path.basename(f): f for f in xml_files}
            
            selected_files = []
            for file_name, file_path in file_options.items():
                if st.checkbox(file_name, value=True):
                    selected_files.append(file_path)
            
            # Import button
            if selected_files and st.button("Import Selected Files"):
                st.subheader("Import Progress")
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                total_imported = 0
                total_files = len(selected_files)
                
                for i, file_path in enumerate(selected_files):
                    status_text.text(f"Importing file {i+1} of {total_files}: {os.path.basename(file_path)}")
                    
                    # Import the file
                    imported_count = process_xml_file(db, file_path)
                    total_imported += imported_count
                    
                    # Update progress
                    progress_bar.progress((i + 1) / total_files)
                
                # Show results
                if total_imported > 0:
                    st.success(f"Successfully imported {total_imported} new measurements from {total_files} files")
                else:
                    st.info("No new measurements were imported (possibly duplicates)")
    else:
        st.warning("Please enter a valid directory path")
    
    # Option to return to main dashboard
    st.markdown("---")
    if st.button("Return to Dashboard"):
        st.switch_page("app.py")

if __name__ == "__main__":
    main()