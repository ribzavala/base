import os
from google.colab import files
from IPython.display import Image, display
import pandas as pd
import json

def upload_images():
    """
    Uploads and saves images into a specified folder.

    Returns:
    None
    """
    folder = 'images'
    # Create the folder if it doesn't exist
    os.makedirs(folder, exist_ok=True)
    # Upload files from the local device
    uploaded = files.upload()
    # Save uploaded files to the specified folder
    for filename in uploaded.keys():
        with open(os.path.join(folder, filename), 'wb') as f:
            f.write(uploaded[filename])

def show_image(index):
    """
    Displays an image by its index from the 'images' folder and prints its layout.

    Parameters:
    index (int): Index of the image to display.

    Returns:
    None
    """
    folder = 'images'
    # List all valid image files in the folder
    image_files = [f for f in os.listdir(folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif'))]

    if 0 <= index < len(image_files):
        img_path = os.path.join(folder, image_files[index])
        print(f"Layout: {image_files[index]}")  # Print the filename before displaying
        display(Image(filename=img_path))  # Display the image
    else:
        print(f"Index out of range. There are only {len(image_files)} images.")

def process_json():
    """
    Processes a JSON file from the 'images' folder and returns a combined DataFrame
    with Master and Slave robot data.

    Returns:
    pd.DataFrame: A combined DataFrame containing Master and Slave robot information.
    """
    folder = 'images'
    # Locate the JSON file in the folder
    json_file = [file for file in os.listdir(folder) if file.endswith('.json')][0]

    # Load the JSON file
    with open(os.path.join(folder, json_file), 'r') as f:
        json_data = json.load(f)

    # Extract the "Measurements" key and convert it to a DataFrame
    measurements = json_data.get("Measurements", [])
    df = pd.DataFrame(measurements)

    # Function to clean the RobotName field
    def clean_robot_name(robot_name):
        return robot_name.replace('+', '').replace('=', '').split('-')[0]

    # Clean the RobotName field for the slaves
    df['RobotName'] = df['RobotName'].apply(clean_robot_name)

    # Get the master RobotName and clean it
    master_robot = json_data.get("RobotName", "")  # Master RobotName is stored outside Measurements
    master_robot_cleaned = clean_robot_name(master_robot)

    # Create a DataFrame for the master robot
    master_row = {
        "RobotName": master_robot_cleaned,
        "Role": "Master",
        "RobotType": json_data.get("RobotType", ""),
        **dict.fromkeys(["X", "Y", "Z", "RX", "RY", "RZ"], "NA"),
        "IP": json_data.get("IP", "NA")  # Include the IP from JSON
    }
    df_master = pd.DataFrame([master_row])

    # Add the Role column to the slave robots
    df['Role'] = 'Slave'

    # Combine Master and Slaves into one DataFrame
    df = pd.concat([df_master, df], ignore_index=True)

    # Reorder the columns to place Role next to RobotName
    columns_order = ['RobotName', 'Role'] + [col for col in df.columns if col not in ['RobotName', 'Role']]
    df = df[columns_order]

    return df

def generate_rosipcfg_xml(df, output_file='ROSIPCFG.xml'):
    """
    Generates an XML configuration file from a DataFrame containing robot data.

    Parameters:
    df (pd.DataFrame): DataFrame containing 'RobotName' and 'IP' columns.
    output_file (str): The name of the output XML file (default: 'ROSIPCFG.xml').

    Returns:
    str: The generated XML content as a string.
    """
    global folder_path  # Ensure the function uses the globally defined folder_path
    folder_path = 'OLP_NET1'
    os.makedirs(folder_path, exist_ok=True)

    # Extract RobotName and IP from the DataFrame
    robot_data = df[['RobotName', 'IP']].to_dict('records')

    # Start building the XML structure as a string
    xml_content = """<ROSIPCFG>
<ROBOTRING count="{count}" timeslot="400">\n""".format(count=len(robot_data))

    # Add each MEMBER entry
    for robot in robot_data:
        xml_content += '    <MEMBER name="{name}" ipadd="{ipadd}"/>\n'.format(
            name=robot["RobotName"], ipadd=robot["IP"]
        )

    # Close the XML structure
    xml_content += "</ROBOTRING>\n</ROSIPCFG>"
    print(xml_content)

    # Save the XML content to a file
    output_file = os.path.join(folder_path, 'ROSIPCFG.xml')
    # Save the XML content to a file
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write(xml_content)

    print(f"\nFile generated {output_file}")
    return xml_content

def generate_xvr_files(df):
    """
    Generates XML files (members.xvr and calib.xvr) from a DataFrame containing robot data.

    Parameters:
    df (pd.DataFrame): DataFrame containing robot data with columns like RobotName, Role, X, Y, Z, RX, RY, RZ.

    Returns:
    None
    """
    # Use the pre-defined folder_path variable (must be defined elsewhere in the script)
    # Ensure folder_path exists

    # Define XML header and footer
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

    output_file = os.path.join(folder_path, 'members.xvr')
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

    output_file = os.path.join(folder_path, 'calib.xvr')
    with open(output_file, "w", encoding="iso-8859-1") as file:
        file.write(xml_content)

    print(f"File generated: {output_file}")

def generate_iic_chk_xml(df):
    """
    Generates the XML file iic_chk.xvr based on a DataFrame containing robot data.

    Parameters:
    df (pd.DataFrame): DataFrame containing robot data with columns like RobotName and Role.

    Returns:
    None
    """
    global folder_path  # Ensure the function uses the globally defined folder_path

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
    output_file = os.path.join(folder_path, 'iic_chk.xvr')
    with open(output_file, "w", encoding="iso-8859-1") as file:
        file.write(xml_content)

    #print(f"File generated: {output_file}")
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

