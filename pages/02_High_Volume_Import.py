import os
import streamlit as st
import glob
import time
import concurrent.futures
from datetime import datetime
from src.xml_parser import XMLParser
from src.data_validator import DataValidator
from src.database import Database

def process_batch(file_paths, db, update_progress=None, start_idx=0):
    """
    Process a batch of XML files
    
    Args:
        file_paths: List of file paths to process
        db: Database instance
        update_progress: Optional progress callback
        start_idx: Starting index for progress calculation
        
    Returns:
        tuple: (successful_imports, failed_imports, duplicate_count)
    """
    successful_imports = 0
    failed_imports = 0
    duplicate_count = 0
    
    for i, file_path in enumerate(file_paths):
        try:
            # Parse XML data
            probe_data_list = XMLParser.parse_xml_file(file_path)
            
            if not probe_data_list:
                failed_imports += 1
                continue
                
            # Process each probe in the file
            for probe_data in probe_data_list:
                # Validate probe data
                is_valid, _ = DataValidator.validate_probe_data(probe_data)
                
                if not is_valid:
                    failed_imports += 1
                    continue
                
                # Check if measurement already exists
                if db.measurement_exists(probe_data['address'], probe_data['datetime']):
                    duplicate_count += 1
                    continue
                    
                # Save to database
                db.save_measurement(probe_data)
                successful_imports += 1
                
            # Update progress if callback provided
            if update_progress and i % 10 == 0:  # Update every 10 files to reduce UI overhead
                update_progress(start_idx + i + 1)
                
        except Exception as e:
            print(f"Error processing file {os.path.basename(file_path)}: {str(e)}")
            failed_imports += 1
    
    return successful_imports, failed_imports, duplicate_count

def main():
    st.set_page_config(page_title="High Volume XML Import", page_icon="📊", layout="wide")
    
    st.title("High Volume XML Import Tool")
    st.write("This tool is optimized for importing large volumes of XML files (thousands of files).")
    
    # Initialize database
    try:
        db = Database()
    except Exception as e:
        st.error(f"Failed to connect to database: {str(e)}")
        return
    
    # UI for selecting directory
    st.header("1. Select XML Files Directory")
    
    # Create a button to directly import the probe 012345 files
    if st.button("Import all probe 012345 XML files"):
        xml_files = glob.glob("attached_assets/006*.xml")
        if xml_files:
            st.success(f"Found {len(xml_files)} XML files for probe 012345")
            xml_dir = "attached_assets"
        else:
            st.warning("No probe 012345 XML files found")
    
    xml_dir = st.text_input("XML Directory Path", value="attached_assets", 
                           help="Enter the directory path containing XML files")
    
    # Find all XML files in the directory
    if xml_dir and os.path.isdir(xml_dir):
        xml_files = glob.glob(os.path.join(xml_dir, "*.xml")) + glob.glob(os.path.join(xml_dir, "*.XML"))
        
        total_files = len(xml_files)
        
        if not xml_files:
            st.warning(f"No XML files found in directory: {xml_dir}")
        else:
            st.success(f"Found {total_files} XML files")
            
            # Configure batch size for processing
            col1, col2 = st.columns(2)
            
            with col1:
                batch_size = st.number_input("Batch Size", 
                                          min_value=10, 
                                          max_value=1000, 
                                          value=100,
                                          help="Number of files to process in each batch")
            
            with col2:
                max_workers = st.number_input("Parallel Workers", 
                                           min_value=1, 
                                           max_value=8, 
                                           value=4,
                                           help="Number of parallel processes (higher values use more CPU)")
            
            # Import button
            if st.button("Start Import Process"):
                start_time = time.time()
                
                # Prepare progress tracking
                st.subheader("Import Progress")
                progress_bar = st.progress(0)
                status_text = st.empty()
                metrics_container = st.empty()
                
                # Initialize counters
                total_imported = 0
                total_failed = 0
                total_duplicates = 0
                
                # Process files in batches
                total_batches = (total_files + batch_size - 1) // batch_size
                
                with st.spinner("Importing files..."):
                    # Create batches
                    batches = [xml_files[i:i+batch_size] for i in range(0, total_files, batch_size)]
                    
                    # Function to update progress
                    def update_progress(file_count):
                        progress = min(file_count / total_files, 1.0)
                        progress_bar.progress(progress)
                        status_text.text(f"Processed {file_count} of {total_files} files ({progress*100:.1f}%)")
                    
                    # Process each batch
                    for batch_idx, batch in enumerate(batches):
                        status_text.text(f"Processing batch {batch_idx+1} of {total_batches}...")
                        
                        # Update metrics periodically
                        with metrics_container.container():
                            cols = st.columns(4)
                            cols[0].metric("Files Processed", f"{min((batch_idx)*batch_size, total_files)} / {total_files}")
                            cols[1].metric("Successful Imports", total_imported)
                            cols[2].metric("Failed Imports", total_failed)
                            cols[3].metric("Duplicates Skipped", total_duplicates)
                        
                        if max_workers > 1 and batch_size >= max_workers:
                            # Split batch for parallel processing
                            sub_batch_size = len(batch) // max_workers
                            sub_batches = [batch[i:i+sub_batch_size] for i in range(0, len(batch), sub_batch_size)]
                            
                            # Start position for progress calculation
                            start_positions = [batch_idx * batch_size + i * sub_batch_size for i in range(len(sub_batches))]
                            
                            # Process in parallel
                            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                                futures = [
                                    executor.submit(
                                        process_batch, 
                                        sub_batch, 
                                        db, 
                                        update_progress,
                                        start_pos
                                    ) 
                                    for sub_batch, start_pos in zip(sub_batches, start_positions)
                                ]
                                
                                # Collect results
                                for future in concurrent.futures.as_completed(futures):
                                    success, fail, duplicates = future.result()
                                    total_imported += success
                                    total_failed += fail
                                    total_duplicates += duplicates
                        else:
                            # Process batch sequentially
                            success, fail, duplicates = process_batch(
                                batch, 
                                db, 
                                update_progress,
                                batch_idx * batch_size
                            )
                            total_imported += success
                            total_failed += fail
                            total_duplicates += duplicates
                        
                        # Update progress bar
                        progress = min((batch_idx + 1) * batch_size, total_files) / total_files
                        progress_bar.progress(progress)
                
                # Calculate time taken
                end_time = time.time()
                time_taken = end_time - start_time
                
                # Show final results
                st.success(f"Import completed in {time_taken:.2f} seconds")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Files Processed", total_files)
                col2.metric("Successfully Imported", total_imported)
                col3.metric("Failed Imports", total_failed)
                col4.metric("Duplicates Skipped", total_duplicates)
                
                if total_imported > 0:
                    st.success(f"Successfully imported {total_imported} new measurements")
                    st.info(f"Processing rate: {total_files/time_taken:.1f} files per second")
                else:
                    st.info("No new measurements were imported (possibly all were duplicates)")
    else:
        st.warning("Please enter a valid directory path")
    
    # Option to return to main dashboard
    st.markdown("---")
    if st.button("Return to Dashboard"):
        st.switch_page("app.py")

if __name__ == "__main__":
    main()