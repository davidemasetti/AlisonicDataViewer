import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional
import streamlit as st

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
                st.error("No Site element found in XML")
                return None

            site_info = {
                'server_id': site.find('ServerID').text if site.find('ServerID') is not None else '',
                'distributor_id': site.find('DistributorID').text if site.find('DistributorID') is not None else '',
                'customer_id': site.find('CustomerID').text if site.find('CustomerID') is not None else '',
                'site_id': site.find('SiteID').text if site.find('SiteID') is not None else ''
            }

            # Find all probes
            probes = root.findall('.//Probe')
            if not probes:
                st.error("No Probe elements found in XML")
                return None

            probe_data_list = []
            for probe in probes:
                # Parse temperatures
                temperatures = probe.find('Temperatures')
                temp_values = []
                if temperatures is not None:
                    temp_values = [float(temp.text) for temp in temperatures.findall('Temperature') if temp.text]

                # Format datetime (replace '.' with ':' for database compatibility)
                datetime_str = probe.find('DateTime').text if probe.find('DateTime') is not None else ''
                if datetime_str:
                    # Replace all dots with colons in the time part for consistent format
                    datetime_str = datetime_str.replace('.', ':')

                # Create probe data dictionary
                # Get Status from old format or ProbeStatus from new format
                status_value = '0'
                status_node = probe.find('Status')
                probe_status_node = probe.find('ProbeStatus')
                
                if probe_status_node is not None and probe_status_node.text:
                    status_value = probe_status_node.text
                elif status_node is not None and status_node.text:
                    status_value = status_node.text
                
                # Get site info - support missing values
                customer_id = site_info.get('customer_id', '1')
                site_id = site_info.get('site_id', '1')
                
                # For files with missing SiteID, use a default consistent value
                if not site_id or site_id.strip() == '':
                    site_id = '999'  # Default site ID for files without site information
                    
                if not customer_id or customer_id.strip() == '':
                    customer_id = '999'  # Default customer ID for files without customer information
                
                probe_data = {
                    'server_id': site_info.get('server_id', ''),
                    'distributor_id': site_info.get('distributor_id', ''),
                    'customer_id': customer_id,
                    'site_id': site_id,
                    'address': probe.find('Address').text if probe.find('Address') is not None else '',
                    'status': status_value,
                    'probe_status': probe_status_node.text if probe_status_node is not None else status_value,
                    'alarm_status': probe.find('AlarmStatus').text if probe.find('AlarmStatus') is not None else '0',
                    'tank_status': probe.find('TankStatus').text if probe.find('TankStatus') is not None else '0',
                    'datetime': datetime_str,
                    'ullage': probe.find('Ullage').text if probe.find('Ullage') is not None else '0.0',
                    'product': probe.find('Product').text if probe.find('Product') is not None else '0.0',
                    'water': probe.find('Water').text if probe.find('Water') is not None else '0.0',
                    'density': probe.find('Density').text if probe.find('Density') is not None else '0.0',
                    'phs': probe.find('Phs').text if probe.find('Phs') is not None else '',
                    'discriminator': probe.find('Discriminator').text if probe.find('Discriminator') is not None and probe.find('Discriminator').text else 'N',
                    'temperatures': temp_values
                }
                probe_data_list.append(probe_data)

            return probe_data_list
        except Exception as e:
            st.error(f"Error parsing XML file: {str(e)}")
            return None