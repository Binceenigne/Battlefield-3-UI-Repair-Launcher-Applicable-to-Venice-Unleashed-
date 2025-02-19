import os
import subprocess
import time
import pymem
import pymem.exception
import sys
import tkinter as tk
from tkinter import messagebox
import win32gui 
import win32process 

def show_error_popup(message):
    root = tk.Tk()
    root.withdraw()  
    messagebox.showerror("[Battlefield 3 UI Fix Launcher] Error", message)
    root.destroy()

def find_target_process_by_window_title(title_prefix):
    def callback(hwnd, hwnds):
        if win32gui.IsWindowVisible(hwnd) and title_prefix in win32gui.GetWindowText(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            hwnds.append(pid)
        return True

    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    return hwnds[0] if hwnds else None

def main():
    # ================= Configuration Section =================
    PROCESS_NAME = "vu.exe"               # Target process name
    WINDOW_TITLE_PREFIX = "Battlefield 3 - Venice Unleashed"  # Part of the window title
    MAX_WAIT_PROCESS = 30                 # Maximum wait time for the process to start (seconds)
    RETRY_INTERVAL = 2                    # Memory check retry interval (seconds)
    MAX_ATTEMPTS = 10                     # Maximum attempts for a single address
    
    # Memory patch configuration
    PATCHES = [
        {   
            "name": "1",
            "address": 0x01766A97,
            "original": bytes.fromhex("81FF0005"),
            "new": bytes.fromhex("81FF00FF")
        },
        {
            "name": "2",
            "address": 0x01766A9F,
            "original": bytes.fromhex("81FBD002"),
            "new": bytes.fromhex("81FBD0FF")
        },
        {
            "name": "3",
            "address": 0x0094FC88,
            "original": bytes.fromhex("81F90005"),
            "new": bytes.fromhex("81F900FF")
        },
        {
            "name": "4",
            "address": 0x0094FC61,
            "original": bytes.fromhex("3DD00200"),
            "new": bytes.fromhex("3DD002FF")
        }
    ]
    # ================= Execution Logic Below =================

    # Get the current working directory
    script_dir = os.getcwd()
    exe_path = os.path.join(script_dir, PROCESS_NAME)

    # Debug information output
    print(f"[System Info] Script directory: {script_dir}")
    print(f"[Path Check] Target path: {exe_path}")
    print(f"[Directory List] Current contents: {os.listdir(script_dir)}")

    # Verify the existence of the target file
    if not os.path.isfile(exe_path):
        print(f"\n[Fatal Error] {PROCESS_NAME} not found")
        print("Possible reasons:")
        print("1. File not placed in the same directory as the script")
        print("2. File name case mismatch (actual name: {0})".format(
            next((f for f in os.listdir(script_dir) if f.lower() == PROCESS_NAME.lower()), "No similar file found")
        ))
        print("3. File hidden or system protected (try un-hiding the file)")
        print("4. Antivirus software blocking")
        show_error_popup(f"[Launch Error] {PROCESS_NAME} not found\nPlease check if {PROCESS_NAME} exists in the script directory.\nPossible reasons:\n1. File not placed in the same directory as the script\n2. File name case mismatch\n3. File hidden or system protected\n4. Antivirus software blocking")
        return

    # Launch the target program
    print(f"\n[Launcher] Starting {PROCESS_NAME}...")
    try:
        subprocess.Popen(exe_path, cwd=script_dir)
    except Exception as e:
        print(f"[Launch Error] Cannot execute program: {str(e)}")
        show_error_popup(f"[Launch Error] Cannot execute program: {str(e)}\nPlease check {PROCESS_NAME}'s system permissions and if the UI fix launcher was started with administrator privileges.")
        return

    # Wait for the process to initialize
    print("\n[Process Monitor] Waiting for the target process to start...")
    pm = None
    start_time = time.time()
    target_pid = None

    while time.time() - start_time < MAX_WAIT_PROCESS:
        try:
            # Find the target process by window title
            target_pid = find_target_process_by_window_title(WINDOW_TITLE_PREFIX)
            if target_pid:
                pm = pymem.Pymem()
                pm.open_process_from_id(target_pid)  # Attach to the process via PID
                print(f"[Process Ready] Successfully attached to process (PID: {target_pid})")
                time.sleep(3)
                break
            else:
                print(f"Waiting... Elapsed time: {int(time.time()-start_time)} seconds", end='\r')
                time.sleep(1)
        except pymem.exception.ProcessNotFound:
            print(f"Waiting... Elapsed time: {int(time.time()-start_time)} seconds", end='\r')
            time.sleep(1)
    else:
        print("\n[Timeout Error] Process did not start within the specified time")
        show_error_popup(f"[Timeout Error] Process did not start within the specified time\nPlease check if {PROCESS_NAME} is running normally and if the UI fix launcher was started with administrator privileges.")
        return

    # Perform memory modifications
    print("\n[Memory Operation] Starting injection...")
    success_count = 0
    error_messages = []  # To store error messages

    for patch in PATCHES:
        attempts = 0
        print(f"\nHandling {patch['name']} ({hex(patch['address'])})")
        current_error = None  # To store the current patch error message

        while attempts < MAX_ATTEMPTS:
            try:
                # Read the current memory value
                current = pm.read_bytes(patch["address"], len(patch["original"]))
                
                if current == patch["original"]:
                    # Perform the write operation
                    pm.write_bytes(patch["address"], patch["new"], len(patch["new"]))
                    # Verify the write
                    verify = pm.read_bytes(patch["address"], len(patch["new"]))
                    if verify == patch["new"]:
                        print(f"  ✓ Successfully wrote {patch['new'].hex().upper()}")
                        success_count += 1
                        break
                    else:
                        print(f"  ! Write verification failed (current value: {verify.hex().upper()})")
                        current_error = f"[Write Error] Write verification failed (current value: {verify.hex().upper()})\n Please check {PROCESS_NAME}'s memory state and if the UI fix launcher was started with administrator privileges."
                else:
                    print(f"  ! Memory mismatch (expected: {patch['original'].hex().upper()}, actual: {current.hex().upper()})")
                    current_error = f"Memory mismatch (expected: {patch['original'].hex().upper()}, actual: {current.hex().upper()})\n Please check {PROCESS_NAME}'s memory state and if any antivirus software is blocking."

                attempts += 1
                if attempts < MAX_ATTEMPTS:
                    time.sleep(RETRY_INTERVAL)
                    
            except Exception as e:
                print(f"  × Operation exception: {str(e)}")
                current_error = f"Operation exception: {str(e)}"
                attempts += 1
                time.sleep(RETRY_INTERVAL)
        else:
            print(f"  × Reached maximum retry attempts ({MAX_ATTEMPTS} times)")
            if current_error:
                error_messages.append(current_error)

    # After all patches have been processed, check for error messages and display a popup
    if error_messages:
        full_error_message = "\n".join(error_messages)
        show_error_popup(full_error_message)
            

    # Cleanup
    pm.close_process()
    print(f"\n[Completion Stats] Successfully injected {success_count}/{len(PATCHES)} patches")
    print("Hint: If injection was not completely successful, please check:")
    print("1. Run the script as an administrator")
    print("2. Open the client before running the server")
    print("3. Close any memory protection software")

if __name__ == "__main__":
    print("=== Memory Modification Tool (run as administrator) ===")
    main()
    print("\n[Hint] The script will automatically exit in 5 seconds, please enjoy the game...")
    time.sleep(5)
    sys.exit()
