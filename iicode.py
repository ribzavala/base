import os
import ipywidgets as widgets
from IPython.display import display
from google.colab import files
import zipfile
from IPython.display import Image, display
import pandas as pd
import json


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
    """
    Sube un archivo ZIP y extrae su contenido directamente
    en la carpeta 'images', que es donde 'show_image' busca los archivos.
    """
    print("--> Por favor, selecciona tu archivo .ZIP.")

    uploaded = files.upload()

    if not uploaded:
        print("\nOperación cancelada.")
        return None

    zip_name = list(uploaded.keys())[0]
    project_folder = os.path.splitext(zip_name)[0]

    try:
        os.makedirs(project_folder, exist_ok=True)
        with zipfile.ZipFile(zip_name, 'r') as zip_ref:
            zip_ref.extractall(project_folder)

        print(f"\n✅ Files extracted to project folder: '{project_folder}'")
        os.remove(zip_name)
        return project_folder

    except Exception as e:
        print(f"\n❌ Error processing ZIP file: {e}")
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
            'FNLL', 'FRAMER_1', 'FRAMER_2', 'Front Door', 'Front Floor',
            'Front Structure', 'Hang_On', 'Hood', 'Lift Gate', 'Re-Spot',
            'Rear Door', 'Rear Floor', 'Underbody_Main'
        ],
        'DU04': ['Assembly', 'Auto Unload', 'Gear', 'Motor', 'Rotor'],
        'PAINT': ['Primer', 'Top_Coat', 'Sealer']
    }

    # 2. Create the widgets
    main_category_dropdown = widgets.Dropdown(
        options=dependent_options.keys(),
        description='Main Category:'
    )
    sub_category_dropdown = widgets.Dropdown(
        options=dependent_options[main_category_dropdown.value],
        description='Sub-Category:'
    )

    # 3. Define the nested update function
    def on_main_category_change(change):
        sub_category_dropdown.options = dependent_options[change['new']]

    # 4. Link the function to the first dropdown
    main_category_dropdown.observe(on_main_category_change, names='value')

    # 5. Display the widgets
    print("Select a category to see its sub-categories:")
    display(widgets.VBox([main_category_dropdown, sub_category_dropdown]))

    # 6. Return the widget objects so you can access their values later
    return main_category_dropdown, sub_category_dropdown


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



def process_json(project_folder):
    """
    Processes the JSON file from the specified project_folder.
    """
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
    
    # Merge with external IP data
    ip_df = ip_json() # Assumes base/IP.json exists from git clone
    final_df = pd.merge(combined_df.drop(columns=['IP'], errors='ignore'), ip_df, on='RobotName', how='left')
    
    final_df = final_df.sort_values(by='RobotName', ignore_index=True)
    return final_df


def ip_json(file_path='base/IP.json'):
    """Reads robot IP data from the 'base' directory."""
    robot_list = []
    with open(file_path, 'r') as f:
        data = json.load(f)
    zones = data.get("SHOP_body", {}).get("ZONE", {})
    for zone_key, zone_content in zones.items():
        robot_name_dict = zone_content.get("robot_name", {})
        if not robot_name_dict: continue
        first_full_name = list(robot_name_dict.keys())[0]
        zone_variable = first_full_name.split('.')[2]
        for full_name, ip in robot_name_dict.items():
            name_part = full_name.split(f'.{zone_variable}.')[-1]
            cleaned_name = name_part.replace('=', '')
            robot_list.append({"RobotName": cleaned_name, "IP": ip})
    return pd.DataFrame(robot_list)


def generate_rosipcfg_xml(df, project_folder,output_file='ROSIPCFG.xml'):
    """
    Generates ROSIPCFG.xml inside the specified project_folder.
    """
    os.makedirs(project_folder, exist_ok=True)
    master_df = df[df['Role'] == 'Master']
    slaves_df = df[df['Role'] == 'Slave']
    sorted_df = pd.concat([master_df, slaves_df], ignore_index=True)
    robot_data = sorted_df[['RobotName', 'IP']].to_dict('records')
    xml_content = f'<ROSIPCFG>\n<ROBOTRING count="{len(robot_data)}" timeslot="400">\n'
    for robot in robot_data:
        ip_address = robot["IP"] if pd.notna(robot["IP"]) else 'NA'
        xml_content += f'    <MEMBER name="{robot["RobotName"]}" ipadd="{ip_address}"/>\n'
    xml_content += "</ROBOTRING>\n</ROSIPCFG>"
    
    full_output_path = os.path.join(project_folder, output_file)
    with open(full_output_path, 'w', encoding='utf-8') as file:
        file.write(xml_content)
    print(f"File generated: {full_output_path}")
    print("\n--- Formatted XML Content ---")
    print(xml_content)


def generate_xvr_files(df, project_folder):
    """
    Generates XML files (members.xvr and calib.xvr) from a DataFrame containing robot data.
    """
    os.makedirs(project_folder, exist_ok=True)

    # Define XML header and footer
    XML_HEADER = '''<?xml version="1.0" encoding="iso-8859-1"?>
<XMLVAR version="V9.30126 2/12/2021">
 <PROG name="*SYSTEM*">
  <VAR name="{var_name}">'''

    XML_FOOTER = '''
  </VAR>
 </PROG>
</XMLVAR>
'''

    # Utility function to format values
    def format_value(value):
        return "0.000000" if value == "NA" else value

    # Generate members.xvr
    var_name = "$IC_AZ_MEMBR"
    xml_content = XML_HEADER.format(var_name=var_name)

    for index, row in df.iterrows():
        role = row['Role']
        member_id = index + 1
        zmgr_name = row['RobotName'] if role == 'Master' else '********'
        member_name = row['RobotName']

        xml_content += f'''
    <ARRAY name = "{var_name}[{member_id}]">
      <FIELD name="$ZMGR_NAME" prot ="RW">{zmgr_name}</FIELD>
      <FIELD name="$MEMBER_NAME" prot ="RW">{member_name}</FIELD>
      <FIELD name="$GROUP" prot ="RW">1</FIELD>
      <FIELD name="$COMMENT" prot ="RW">{role}</FIELD>
    </ARRAY>'''

    xml_content += XML_FOOTER

    output_file = os.path.join(project_folder, 'members.xvr')
    with open(output_file, "w", encoding="iso-8859-1") as file:
        file.write(xml_content)

    print(f"File generated: {output_file}")

    # Generate calib.xvr
    var_name = "$IC_AZ_CALIB"
    xml_content = XML_HEADER.format(var_name=var_name)

    for index, row in df.iterrows():
        role = row['Role']
        member_id = index + 1
        calib_done = "TRUE" if role == "Master" else "FALSE"
        x_value, y_value, z_value = map(format_value, [row['X'], row['Y'], row['Z']])
        rx_value, ry_value, rz_value = map(format_value, [row['RX'], row['RY'], row['RZ']])

        xml_content += f'''
    <ARRAY name = "{var_name}[{member_id}]">
      <FIELD name="$CALIB_DONE" prot ="RW">{calib_done}</FIELD>
      <FIELD name="$CALIB_FRAME" prot ="RW">
  gnum: 1 rep: 1 axes: 0 utool: 255 uframe: 255 Config: N D B, 0, 0, 0
  X:      {x_value}   Y:      {y_value}   Z:      {z_value}
  W:      {rx_value}   P:      {ry_value}   R:      {rz_value}</FIELD>
      <FIELD name="$ROB1_NAME" prot ="RW">{df.iloc[0]['RobotName']}</FIELD>
      <FIELD name="$ROB2_NAME" prot ="RW">{row['RobotName']}</FIELD>
    </ARRAY>'''

    xml_content += XML_FOOTER

    output_file = os.path.join(project_folder, 'calib.xvr')
    with open(output_file, "w", encoding="iso-8859-1") as file:
        file.write(xml_content)

    print(f"File generated: {output_file}")

def generate_iic_chk_xml(df, project_folder):
    """
    Generates the XML file iic_chk.xvr based on a DataFrame containing robot data.
    """
    os.makedirs(project_folder, exist_ok=True)

    # Define the variable name and XML header/footer
    var_name = "$IA_CHKCMB"
    XML_HEADER = '''<!-- <Rivian code gen 1.0" /> -->
    <?xml version="1.0" encoding="iso-8859-1"?>
    <XMLVAR version="V9.30126 2/12/2021">
      <PROG name="*SYSTEM*">
        <VAR name="{var_name}">'''
    
    XML_FOOTER = '''
        </VAR>
      </PROG>
    </XMLVAR>
    '''

    # Start building the XML content
    xml_content = XML_HEADER.format(var_name=var_name)

    # Dynamically construct ARRAY sections for the specific structure
    for index, row in df.iterrows():
        member_id = index + 1
        member_name = row['RobotName']

        xml_content += f"""
        <ARRAY name = "{var_name}[{member_id}]">
        <FIELD name="$R_CNTLR" prot ="RW">{member_name}</FIELD>
        </ARRAY>"""

    # Add the footer to the XML content
    xml_content += XML_FOOTER

    # Define the output file path
    output_file = os.path.join(project_folder, 'iic_chk.xvr')
    with open(output_file, "w", encoding="iso-8859-1") as file:
        file.write(xml_content)

    print(f"File generated: {output_file}")
    return xml_content


def copy_and_zip_folder():
    """
    Copies the iic_chkbase.xvr file from the base folder to the output folder
    and zips the entire folder into a single ZIP file.

    Returns:
    None
    """
    global folder_path  # Use the existing folder_path variable

    # Ensure the base folder and file exist
    base_folder = "base"
    base_file = os.path.join(base_folder, "iic_chkbase.xvr")
    if not os.path.exists(base_file):
        print(f"Base file {base_file} not found. Please ensure it exists.")
        return

    # Copy the base file to the output folder
    destination_file = os.path.join(folder_path, "iic_chkbase.xvr")
    os.makedirs(folder_path, exist_ok=True)  # Ensure the folder exists
    with open(base_file, "rb") as src, open(destination_file, "wb") as dst:
        dst.write(src.read())
    print(f"Copied {base_file} to {destination_file}")

    # Create a ZIP archive of the folder
    zip_file_path = f"{folder_path}.zip"
    os.system(f"zip -r {zip_file_path} {folder_path}")
    print(f"ZIP file created: {zip_file_path}. Please download the file.")

