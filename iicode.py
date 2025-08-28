import os
import ipywidgets as widgets
from IPython.display import display
from google.colab import files
import zipfile
from IPython.display import Image, display
import pandas as pd
import json
import datetime
# --- Global Configuration ---
VERSION = "V2.0"



def get_timestamp():
    """Generates a formatted timestamp string (e.g., '2025-07-20 16:11:11')."""
    return datetime.datetime.now().strftime("%m-%d %H:%M")

def cloned_files(folder):
    """
    Copies files (images and .json) from a specified directory to the 'images' folder.
    """
    images_folder = 'images'
    os.makedirs(images_folder, exist_ok=True)

    if not os.path.exists(folder):
        print(f"Error: The source folder '{folder}' does not exist in the Colab environment.")
        return

    valid_files = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.json'))]
    if not valid_files:
        print(f"No valid files found in the source folder '{folder}'.")
        return

    for file in valid_files:
        src_path = os.path.join(folder, file)
        dest_path = os.path.join(images_folder, file)
        with open(src_path, 'rb') as src_file, open(dest_path, 'wb') as dest_file:
            dest_file.write(src_file.read())

    print(f"Successfully copied {len(valid_files)} files to the '{images_folder}' folder.")

def upload_images():

    print("--> Select your .ZIP or .7z file.")

    uploaded = files.upload()

    if not uploaded:
        print("\ncanceled.")
        return None

    zip_name = list(uploaded.keys())[0]
    project_folder = os.path.splitext(zip_name)[0]

    try:
        os.makedirs(project_folder, exist_ok=True)

        # Check the file extension and use the appropriate extractor
        if zip_name.endswith('.zip'):
            with zipfile.ZipFile(zip_name, 'r') as zip_ref:
                zip_ref.extractall(project_folder)
        elif zip_name.endswith('.7z'):
            with py7zr.SevenZipFile(zip_name, mode='r') as z:
                z.extractall(path=project_folder)
        else:
            print(f"\n❌ Unsupported file format. Please upload a .zip or .7z file.")
            os.remove(zip_name)
            return None

        print(f"\n✅ Files extracted to project folder: '{project_folder}'")
        os.remove(zip_name)
        return project_folder

    except Exception as e:
        print(f"\n❌ Error processing file: {e}")
        return None

def select_zone():
    """
    Creates and displays a set of dependent dropdowns for zone selection
    and returns the widget objects.
    """
    # 1. Define all possible options inside the function
    dependent_options = {
        'BL03': [
            'Battery_Tray', 'Battery_Deep_Lid', 'Bodyside_Outer', 'D_RING',
            'FNLL', 'FRAMER_1', 'FRAMER_2', 'Front_Door', 'Front_Floor',
            'Front_Structure', 'Hang_On', 'Hood', 'Lift_Gate', 'Re_Spot',
            'Rear_Door', 'Rear_Floor', 'Underbody_Main'
        ],
        'DU04': ['Assembly', 'Auto Unload', 'Gear', 'Motor', 'Rotor'],
        'PAINT': ['Primer', 'Top_Coat', 'Sealer']
    }

    # 2. Create the widgets
    main_selection = widgets.Dropdown(
        options=dependent_options.keys(),
        description='Main Category:'
    )
    sub_selection = widgets.Dropdown(
        options=dependent_options[main_selection.value],
        description='Sub-Category:'
    )

    # 3. Define the nested update function
    def on_main_category_change(change):
        sub_selection.options = dependent_options[change['new']]

    # 4. Link the function to the first dropdown
    main_selection.observe(on_main_category_change, names='value')

    # 5. Display the widgets
    print("Select a category to see its sub-categories:")
    display(widgets.VBox([main_selection, sub_selection]))

    # 6. Return the widget objects so you can access their values later
    return main_selection, sub_selection


def show_image(project_folder,index):
    """
    Displays an image by its index from the specified project_folder.
    """
    image_files = [f for f in os.listdir(project_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    if 0 <= index < len(image_files):
        img_path = os.path.join(project_folder, image_files[index])
        print(f"Displaying: {image_files[index]}")
        display(Image(filename=img_path))
    else:
        print(f"Index out of range. There are only {len(image_files)} images in '{project_folder}'.")



def process_json(project_folder,main_selection, sub_selection):
    """
    Processes the JSON file from the specified project_folder and merges
    it with the filtered IP data based on user selection.
    
    NOTE: The function signature has been updated to accept dropdown selections.
    """
    main_value = main_selection.value
    sub_value = sub_selection.value
    try:
        json_file_name = [f for f in os.listdir(project_folder) if f.endswith('.json')][0]
        json_path = os.path.join(project_folder, json_file_name)
        with open(json_path, 'r') as f:
            json_data = json.load(f)
    except (FileNotFoundError, IndexError):
        print(f"Error: Could not find a .json file in the folder '{project_folder}'.")
        return None

    measurements = json_data.get("Measurements", [])
    df = pd.DataFrame(measurements)

    def clean_robot_name(robot_name):
        return robot_name.replace('+', '').replace('=', '').split('-')[0].split('%')[0]

    df['RobotName'] = df['RobotName'].apply(clean_robot_name)
    master_robot = json_data.get("RobotName", "")
    master_robot_cleaned = clean_robot_name(master_robot)

    master_row = {
        "RobotName": master_robot_cleaned,
        "Role": "Master",
        "RobotType": json_data.get("RobotType", ""),
        **dict.fromkeys(["X", "Y", "Z", "RX", "RY", "RZ"], "NA"),
        "IP": json_data.get("IP", "NA")
    }
    df_master = pd.DataFrame([master_row])
    df['Role'] = 'Slave'
    combined_df = pd.concat([df_master, df], ignore_index=True)
    
    # MODIFICATION: Call ip_json with the user's selections from the dropdowns.
    # This assumes 'IP.json' is in the same directory.
    # If it is in a 'base' folder, change the path to 'base/IP.json'.
    ip_df = ip_json(main_value, sub_value, file_path='base/IP.json')
    final_df = pd.merge(combined_df.drop(columns=['IP'], errors='ignore'), ip_df, on='RobotName', how='left')

    final_df = final_df.sort_values(by='RobotName', ignore_index=True)
    return final_df


def ip_json(main_selection, sub_selection, file_path='base/IP.json'):
    """
    Reads robot IP data from the provided JSON file, filtering by the selected zone.

    NOTE: The function signature and logic have been updated to filter
    based on the main and sub category selections.
    """
    robot_list = []
    # Construct the search key from the dropdown selections.
    # Example: 'BL03' + ' ' + 'Battery_Tray' -> 'BL03 Battery_Tray'
    search_key = f"{main_selection}_{sub_selection}"

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The IP file was not found at '{file_path}'.")
        return pd.DataFrame()

    zones = data.get("SHOP_body", {}).get("ZONE", {})
    
    # Iterate through all zones in the JSON file.
    for zone_key, zone_content in zones.items():
        # Check if the current zone_key from the file starts with the desired search_key.
        # This handles cases like 'Bodyside_Outer' matching both
        # 'BL03 Bodyside_Outer_Left' and 'BL03 Bodyside_Outer_Right'.
        if zone_key.startswith(search_key):
            robot_name_dict = zone_content.get("robot_name", {})
            if not robot_name_dict: continue

            # The following logic for parsing robot names is kept from your original function.
            first_full_name = list(robot_name_dict.keys())[0]
            zone_variable = first_full_name.split('.')[2]

            for full_name, ip in robot_name_dict.items():
                name_part = full_name.split(f'.{zone_variable}.')[-1]
                # Added .strip() to remove potential leading/trailing spaces.
                cleaned_name = name_part.replace('+', '').replace('=', '').split('-')[0].split('%')[0].strip()
                robot_list.append({"RobotName": cleaned_name, "IP": ip})
                
    return pd.DataFrame(robot_list, columns=['RobotName', 'IP'])



def generate_rosipcfg_xml(df, project_folder,output_file='ROSIPCFG.xml'):
    """
    Generates ROSIPCFG.xml.
    """
    VERSION = "V2.0"
    current_time = get_timestamp()
    os.makedirs(project_folder, exist_ok=True)
    master_df = df[df['Role'] == 'Master']
    slaves_df = df[df['Role'] == 'Slave']
    sorted_df = pd.concat([master_df, slaves_df], ignore_index=True)
    robot_data = sorted_df[['RobotName', 'IP']].to_dict('records')

    xml_content = f'<!-- <Rivian AG {VERSION} - {current_time} -iic setup /> -->\n<ROSIPCFG>\n<ROBOTRING count="{len(robot_data)}" timeslot="400">\n'
    for robot in robot_data:
        ip_address = robot["IP"] if pd.notna(robot["IP"]) else 'NA'
        xml_content += f'    <MEMBER name="{robot["RobotName"]}" ipadd="{ip_address}"/>\n'
    xml_content += "</ROBOTRING>\n</ROSIPCFG>"
    
    full_output_path = os.path.join(project_folder, output_file)
    with open(full_output_path, 'w', encoding='utf-8') as file:
        file.write(xml_content)

    print(f"File generated: {full_output_path}")
    print(xml_content)




def generate_xvr_files(df, project_folder):
    """
    Generates a single, combined XML file (members.xvr) containing both the
    $IC_AZ_MEMBR and $IC_AZ_CALIB variable configurations.
    """
    VERSION = "V2.0"
    current_time = get_timestamp()
    os.makedirs(project_folder, exist_ok=True)



    master_df = df[df['Role'] == 'Master']
    slaves_df = df[df['Role'] == 'Slave']
    sorted_df = pd.concat([master_df, slaves_df], ignore_index=True)
   

    # --- XML Structure ---
    XML_HEADER = f'''<!-- <Rivian AG {VERSION} - {current_time} iic setup /> -->\n<?xml version="1.0" encoding="iso-8859-1"?>
<XMLVAR version="V9.30126 2/12/2021">
    <PROG name="*SYSTEM*">'''

    XML_FOOTER = '''
    </PROG>
</XMLVAR>'''

    # Utility function to format coordinate values
    def format_value(value):
        return "0.000000" if value == "NA" else value

    # --- building the XML content ---
    xml_content = XML_HEADER

    # --- Block 1: $IC_AZ_MEMBR ---
    var_name_membr = "$IC_AZ_MEMBR"
    xml_content += f'\n        <VAR name="{var_name_membr}">'
    for index, row in sorted_df.iterrows():
        member_id = index + 1
        robot_name = row['RobotName']
        role = row['Role']
        xml_content += f'''
            <ARRAY name = "{var_name_membr}[{member_id}]">
                <FIELD name="$ZMGR_NAME" prot ="RW">{robot_name}</FIELD>
                <FIELD name="$MEMBER_NAME" prot ="RW">{robot_name}</FIELD>
                <FIELD name="$GROUP" prot ="RW">1</FIELD>
                <FIELD name="$COMMENT" prot ="RW">{role}</FIELD>
            </ARRAY>'''
    xml_content += '\n        </VAR>'

    # --- Block 2: $IC_AZ_CALIB ---
    var_name_calib = "$IC_AZ_CALIB"
    xml_content += f'\n        <VAR name="{var_name_calib}">'

    master_robot_name = sorted_df.iloc[0]['RobotName']

    for index, row in sorted_df.iterrows():
        member_id = index + 1
        x_value, y_value, z_value = map(format_value, [row['X'], row['Y'], row['Z']])
        rx_value, ry_value, rz_value = map(format_value, [row['RX'], row['RY'], row['RZ']])
        xml_content += f'''
            <ARRAY name = "{var_name_calib}[{member_id}]">
                <FIELD name="$CALIB_DONE" prot ="RW">TRUE</FIELD>
                <FIELD name="$CALIB_FRAME" prot ="RW">
   gnum: 1 rep: 1 axes: 0 utool: 255 uframe: 255 Config: N D B, 0, 0, 0
   X:       {x_value}   Y:       {y_value}   Z:       {z_value}
   W:       {rx_value}   P:       {ry_value}   R:       {rz_value}</FIELD>
                <FIELD name="$ROB1_NAME" prot ="RW">{master_robot_name}</FIELD>
                <FIELD name="$ROB2_NAME" prot ="RW">{row['RobotName']}</FIELD>
            </ARRAY>'''
    xml_content += '\n        </VAR>'

    # --- Block 3: $IA_CHKCMB  ---
    var_name_ia = "$IA_CHKCMB"
    xml_content += f'\n        <VAR name="{var_name_ia}">'
    for index, row in sorted_df.iterrows():
        member_id = index + 1
        member_name = row['RobotName']
        xml_content += f"""
            <ARRAY name = "{var_name_ia}[{member_id}]">
                <FIELD name="$R_CNTLR" prot ="RW">{member_name}</FIELD>
            </ARRAY>"""
    xml_content += '\n        </VAR>'

    # --- Block 4: $IB_CHKCMB  ---
    var_name_ib = "$IB_CHKCMB"
    xml_content += f'\n        <VAR name="{var_name_ib}">'
    for index, row in sorted_df.iterrows():
        member_id = index + 1
        member_name = row['RobotName']
        xml_content += f"""
            <ARRAY name = "{var_name_ib}[{member_id}]">
                <FIELD name="$R_CNTLR" prot ="RW">{member_name}</FIELD>
            </ARRAY>"""
    xml_content += '\n        </VAR>'

    # --- Finalize and write the single file ---
    xml_content += XML_FOOTER
    
    # This function now only creates one file.
    output_file = os.path.join(project_folder, 'calibration.xvr')
    with open(output_file, "w", encoding="iso-8859-1") as file:
        file.write(xml_content)
   
     
    print(f"$IC_AZ_CALIB")
    print(f"$IC_AZ_MEMBR")
    print(f"$IA_CHKCMB")
    print(f"file generated: {output_file}")


def copy_and_zip_folder(project_folder):

    """
    Copies the iic_chkbase.xvr file from the 'base' folder into the project_folder
    and then zips the entire project_folder for download.
    """
    # Ensure the base folder and file exist
    base_folder = "base"
    base_file = os.path.join(base_folder, "iic_chkbase.xvr")
    if not os.path.exists(base_file):
        print(f"Base file {base_file} not found. Please ensure the 'base' repository is cloned.")
        return
    
    # Copy the base file to the output folder
    destination_file = os.path.join(project_folder, "iic_chkbase.xvr")
    os.makedirs(project_folder, exist_ok=True)  # Ensure the folder exists
    with open(base_file, "rb") as src, open(destination_file, "wb") as dst:
        dst.write(src.read())
    print(f"Copied {base_file} to {destination_file}")

    # Create a ZIP archive of the folder
    zip_file_path = f"IIC_AG_{project_folder}.zip"
    os.system(f"zip -r {zip_file_path} {project_folder}")
    
    print(f"\n✅ All files have been processed and zipped into: {zip_file_path}")
    print("Please download this file from the file explorer on the left.")

