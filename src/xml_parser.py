import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional, Any
import streamlit as st
import os

class XMLParser:
    @staticmethod
    def parse_xml_file(file_path: str) -> Optional[List[Dict]]:
        try:
            # Parse XML file
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Get site information
            site = root.find('.//Site')
            if site is None:
                st.error(f"No Site element found in XML file: {os.path.basename(file_path)}")
                return None

            site_info = {
                'server_id': XMLParser._get_element_text(site, 'ServerID', ''),
                'distributor_id': XMLParser._get_element_text(site, 'DistributorID', ''),
                'customer_id': XMLParser._get_element_text(site, 'CustomerID', ''),
                'site_id': XMLParser._get_element_text(site, 'SiteID', '')
            }

            # Find all probes
            probes = root.findall('.//Probe')
            if not probes:
                st.error(f"No Probe elements found in XML file: {os.path.basename(file_path)}")
                return None

            probe_data_list = []
            for probe in probes:
                # Parse temperatures
                temperatures = probe.find('Temperatures')
                temp_values = []
                if temperatures is not None:
                    temp_values = [float(temp.text) for temp in temperatures.findall('Temperature') if temp.text]

                # Format datetime (replace '.' with ':' for database compatibility)
                datetime_str = XMLParser._get_element_text(probe, 'DateTime', '')
                if datetime_str:
                    datetime_str = datetime_str.replace('.', ':')

                # Handle different XML formats - try to get ProbeStatus first, if not found try Status
                probe_status = XMLParser._get_element_text(probe, 'ProbeStatus', None)
                if probe_status is None:
                    probe_status = XMLParser._get_element_text(probe, 'Status', '0')

                # Create probe data dictionary
                probe_data = {
                    'server_id': site_info['server_id'],
                    'distributor_id': site_info['distributor_id'],
                    'customer_id': site_info['customer_id'],
                    'site_id': site_info['site_id'],
                    'address': XMLParser._get_element_text(probe, 'Address', ''),
                    'probe_status': probe_status,
                    'alarm_status': XMLParser._get_element_text(probe, 'AlarmStatus', '0'),
                    'tank_status': XMLParser._get_element_text(probe, 'TankStatus', '0'),
                    'datetime': datetime_str,
                    'ullage': XMLParser._get_element_text(probe, 'Ullage', '0.0'),
                    'product': XMLParser._get_element_text(probe, 'Product', '0.0'),
                    'water': XMLParser._get_element_text(probe, 'Water', '0.0'),
                    'density': XMLParser._get_element_text(probe, 'Density', '0.0'),
                    'phs': XMLParser._get_element_text(probe, 'Phs', ''),
                    'discriminator': XMLParser._get_element_text(probe, 'Discriminator', 'N'),
                    'temperatures': temp_values
                }
                probe_data_list.append(probe_data)

            return probe_data_list
        except Exception as e:
            st.error(f"Error parsing XML file {os.path.basename(file_path)}: {str(e)}")
            return None
    
    @staticmethod
    def _get_element_text(element: Any, tag_name: str, default_value: Any) -> Any:
        """
        Helper method to safely get element text with fallback to default value
        
        Args:
            element: The parent XML element
            tag_name: The tag name of the child element to find
            default_value: The default value to return if element not found
            
        Returns:
            The text content of the element or default value
        """
        child = element.find(tag_name)
        if child is not None and child.text:
            return child.text
        return default_value