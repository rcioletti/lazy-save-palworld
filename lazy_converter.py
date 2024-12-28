import os
import shutil
import subprocess
import zipfile
import ijson
import threading
import customtkinter
from PIL import Image
from tkinter import messagebox

import dependencies.save_extractor.main as SaveExtractor

saves = []

# Event to signal when SaveExtractor is complete
save_extractor_done = threading.Event()
save_converter_done = threading.Event()

def get_save_game_pass(button):
    print("Fetching save from Game Pass...")

    button.destroy()
    progressbar = customtkinter.CTkProgressBar(master=window)
    progressbar.place(relx=0.5, rely=0.65, anchor="center")
    progressbar.set(0.0)

    # Start the background task for zip file checking and save extraction
    threading.Thread(target=check_for_zip_files, daemon=True).start()
    threading.Thread(target=check_progress, args=(progressbar,), daemon=True).start()

def check_progress(progressbar):
    # Check if SaveExtractor is done
    print("checking")
    if save_extractor_done.is_set():
        progressbar.set(0.5)  # Update progressbar when extraction is complete
        # After extraction is done, trigger the save conversion process
        print("convert save")
        threading.Thread(target=convert_save_files, args=(progressbar,), daemon=True).start()
    else:
        # Check again after 1000ms if the extractor is done
        window.after(1000, check_progress, progressbar)

def convert_save_files(progressbar):
    saveFolders = list_folders_in_directory("./saves")
    if not saveFolders:
        print("No folders")
        return
    
    print(saveFolders)

    saveList = []

    for index, saveName in enumerate(saveFolders):
        
        name = convert_sav_JSON(saveName)
        
        if name:
            saveList.append(name)
        
    update_combobox(saveList)
    progressbar.destroy()
    print("progress bar destroyed")

def update_combobox(saveList):

    global saves
    saves = saveList

    if saves:
        combobox = customtkinter.CTkComboBox(master=window, values=saves, width=320,
            font=("Arial", 14))
        combobox.place(relx=0.5, rely=0.5, anchor="center")
        combobox.set("Choose a save to convert:")

        button = customtkinter.CTkButton(window, width=200, text="Convert Save", command=lambda: convert_JSON_sav(combobox.get()))
        button.place(relx=0.5, rely=0.8, anchor="center") 

def run_save_extractor():
    SaveExtractor.main()
    print("SaveExtractor complete")
    save_extractor_done.set()  # Signal that SaveExtractor is done

def check_for_zip_files():
    if not find_zip_files("./"):
        print("Fetching zip files from local directory...")
        threading.Thread(target=run_save_extractor, daemon=True).start()
    else:
        process_zip_files()
        save_extractor_done.set()

def process_zip_files():
    if is_folder_empty("./saves"):
        zip_files = find_zip_files("./")
        print(zip_files)
        unzip_file(zip_files[0], "./saves")

def list_folders_in_directory(directory):
    """Lists all folders in the given directory."""
    try:
        all_items = os.listdir(directory)
        folders = [item for item in all_items if os.path.isdir(os.path.join(directory, item))]
        return folders
    except FileNotFoundError:
        print(f"The directory {directory} does not exist.")
        return []
    except PermissionError:
        print(f"You don't have permission to access {directory}.")
        return []
    
def find_key_in_json(file_path, target_key):

        try:
            with open(file_path, 'r') as f:
                parser = ijson.parse(f)
                value = None
                for prefix, event, val in parser:
                    if event == 'map_key' and val == target_key:
                        prefix, event, value = next(parser)
                        return value
                return value
        except FileNotFoundError:
            print(f"Error: File not found at path: {file_path}")
            return False
        except ijson.common.IncompleteJSONError:
            print(f"Error: Incomplete or invalid JSON in file: {file_path}")
            return False
        return False

def is_folder_empty(directory):
    """Check if the specified directory is empty."""
    try:
        all_items = os.listdir(directory)
        if not all_items:
            return True
        else:
            return False
    except FileNotFoundError:
        print(f"The directory {directory} does not exist.")
        return False
    except PermissionError:
        print(f"You don't have permission to access {directory}.")
        return False

def find_zip_files(directory):
    """Scan a directory and return a list of zip files."""
    zip_files = []
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            if filename.endswith(".zip") and filename.startswith("palworld_"):
                zip_file_path = os.path.join(directory, filename)
                if is_valid_zip(zip_file_path):
                    zip_files.append(filename)
    else:
        print(f"Directory {directory} does not exist.")
    return zip_files

def is_valid_zip(zip_file_path):
    """Check if a file is a valid zip file."""
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.testzip()
        return True
    except zipfile.BadZipFile:
        return False

def unzip_file(zip_file_path, extract_to_folder):
    """Unzip the provided file to the given folder."""
    print(f"Unzipping {zip_file_path} to {extract_to_folder}...")
    os.makedirs(extract_to_folder, exist_ok=True)
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to_folder)
        print(f"Extracted all files to {extract_to_folder}")

def convert_sav_JSON(saveName):
    print(f"Converting .sav file to JSON: {saveName}")
    command = ["python", "./dependencies/save_tools/convert.py", f"./saves/{saveName}/Level/01.sav"]
    try:
        subprocess.run(command, check=True)
        print("Command executed successfully")

        json_file_path = f"./saves/{saveName}/Level/01.sav.json"

        key_found = find_key_in_json(json_file_path, "player_name")
        print(f"Player name found: {key_found}")
        return f"{key_found} - {saveName}"
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        return None

def convert_JSON_sav(saveName):
    print(f"Converting JSON file to .sav: {saveName}")
    command = ["python", "./dependencies/save_tools/convert.py", f"./saves/{saveName}/Level/01.sav.json", "--output", f"./saves/{saveName}/Level.sav"]
    try:
        subprocess.run(command, check=True)
        print("Command executed successfully")
        os.remove(f"./saves/{saveName}/Level/01.sav.json")
        print(f"Deleted JSON file: ./saves/{saveName}/Level/01.sav.json")
        move_save_steam(saveName)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")

def move_save_steam(saveName):
    print("Moving save file to Steam...")
    local_app_data_path = os.path.expandvars(r"%localappdata%\Pal\Saved\SaveGames")
    
    try:
        if not os.path.exists(local_app_data_path):
            raise FileNotFoundError(f"SaveGames directory does not exist at {local_app_data_path}")
        subdirs = [d for d in os.listdir(local_app_data_path) if os.path.isdir(os.path.join(local_app_data_path, d))]
        
        if not subdirs:
            raise FileNotFoundError(f"No subdirectories found in {local_app_data_path}")
        
        target_folder = os.path.join(local_app_data_path, subdirs[0])
        print(f"Detected target folder: {target_folder}")
        source_folder = os.path.join("./saves", saveName)

        shutil.copytree(source_folder, target_folder, dirs_exist_ok=True)
        print(f"Save folder copied to {target_folder}")
        
        messagebox.showinfo("Success", f"Your save is migrated to your Steam game. Launch your game through Steam")
    except Exception as e:
        print(f"Error copying save folder: {e}")
        messagebox.showerror("Error", f"Failed to copy the save folder: {e}")

window = customtkinter.CTk()
window.title("Palworld Save Converter")
window.iconbitmap("./static/pal.ico")

screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()

app_width = 400
app_height = 200

x = (screen_width // 2) - (app_width // 2)
y = (screen_height // 2) - (app_height // 2)

window.geometry(f"{app_width}x{app_height}+{x}+{y}")

overlay_frame = customtkinter.CTkFrame(window, fg_color="transparent")
overlay_frame.place(relx=0.5, rely=0.1, anchor="n")

xgp = customtkinter.CTkImage(dark_image=Image.open("./static/xgp.png"), size=(80,40)) 
steam = customtkinter.CTkImage(dark_image=Image.open("./static/steam.png"), size=(30,30))

label = customtkinter.CTkLabel(overlay_frame , image=xgp, text="")
label.pack(side="left", padx=10)
label = customtkinter.CTkLabel(overlay_frame , image=steam, text="")
label.pack(side="left", padx=10) 

buttonGetSaves = customtkinter.CTkButton(master=window, width=200, text="Get Saves", command=lambda: get_save_game_pass(buttonGetSaves))
buttonGetSaves.place(relx=0.5, rely=0.65, anchor="center")

# Start the Tkinter event loop
window.mainloop()
