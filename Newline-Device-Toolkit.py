import requests
import pyperclip
import time
import os
import re

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_bearer_token():
    """Get bearer token from clipboard or manual input."""
    clipboard = pyperclip.paste().strip()
    
    if re.match(r'^eyJ[a-zA-Z0-9-_]+\.[a-zA-Z0-9-_]+\.[a-zA-Z0-9-_]+$', clipboard):
        print(f"Token grabbed from clipboard: {clipboard[:20]}...")
        input("Press Enter to continue.")
        return clipboard
    else:
        print("No valid token found in clipboard.")
        return input("Paste your Bearer token: ").strip()

def get_base_headers(token):
    """Return base headers for API requests."""
    return {
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {token}",
        "Referer": "https://newline.glbth.com/",
        "Origin": "https://newline.glbth.com",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:142.0) Gecko/20100101 Firefox/142.0",
        "account": "gcisd",
        "accountuser": "<YOUR_ADMIN_EMAIL>",
        "oem": "newline"
    }

def get_devices_with_filter(token, filter_nodes):
    """Fetch devices with custom filter criteria using pagination."""
    url = "https://newline.glbth.com/rest/manager/getalldeviceswithfilter"
    headers = get_base_headers(token)
    jt_page_size = 100
    jt_start_index = 0
    all_devices = []
    total_expected = None

    while True:
        params = {
            "jtSorting": "asc",
            "jtStartIndex": jt_start_index,
            "jtPageSize": jt_page_size,
            "sortcolumn": "label",
            "sortdirection": "asc"
        }
        payload = {
            "rootNode": {
                "@class": "viso.model.entities.filters.FilterGroup",
                "nodes": filter_nodes,
                "type": "AND"
            },
            "name": "",
            "description": "",
            "isGroupFilter": False,
            "private": False,
            "color": "gray",
            "icon": "pe-7s-smile",
            "type": "AND"
        }

        try:
            response = requests.post(url, headers=headers, params=params, json=payload)
            if response.status_code != 200:
                print(f"Error: Status {response.status_code}")
                print(response.text)
                break

            response.encoding = 'utf-8'
            print(f"DEBUG response: {response.text[:500]}")  # ← add this
            data = response.json()
            data = response.json()
            records = data.get("Records", [])
            if not records:
                break

            if total_expected is None:
                total_expected = data.get("TotalRecordCount", None)
                print(f"Total filtered devices: {total_expected}")

            all_devices.extend(records)
            print(f"Fetched {len(all_devices)}/{total_expected} filtered devices...")

            jt_start_index += jt_page_size
            if total_expected and len(all_devices) >= total_expected:
                break

        except Exception as e:
            print(f"Error fetching filtered devices: {str(e)}")
            break

    return all_devices

def get_all_devices(token):
    """Fetch all devices with pagination."""
    url = "https://newline.glbth.com/rest/manager/getalldevices"
    headers = get_base_headers(token)
    
    jt_page_size = 100
    jt_start_index = 0
    page_token = None
    all_devices = []
    total_expected = None
    
    try:
        while True:
            params = {
                "jtStartIndex": jt_start_index,
                "jtPageSize": jt_page_size,
                "jtSorting": "asc",
                "sortcolumn": "label",
                "sortdirection": "asc",
                "calldbyuser": "true"
            }
            
            if page_token:
                params["pageToken"] = page_token
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                print(f"Error: Status {response.status_code} at index {jt_start_index}")
                break
            
            response.encoding = 'utf-8'
            data = response.json()
            records = data.get("Records", [])
            
            if not records:
                break
            
            if total_expected is None:
                total_expected = data.get("TotalRecordCount", None)
                print(f"Total devices: {total_expected}")
            
            all_devices.extend(records)
            print(f"Fetched {len(all_devices)}/{total_expected} devices...")
            
            jt_start_index += jt_page_size
            
            raw_token = records[-1].get("paginationToken", None)
            page_token = f"+{raw_token}" if raw_token else None
            
            if total_expected and len(all_devices) >= total_expected:
                break
        
        print(f"Successfully fetched {len(all_devices)} devices\n")
        return all_devices
        
    except Exception as e:
        print(f"Error fetching devices: {str(e)}")
        return all_devices

def build_filter():
    """Interactive filter builder."""
    filter_nodes = []
    
    print("\n=== Build Custom Filter ===\n")
    
    while True:
        print("\nAvailable filter types:")
        print("1. Tag")
        print("2. Firmware Version")
        print("3. Model")
        print("4. Done (apply filter)")
        
        choice = input("\nAdd filter condition (1-4): ").strip()
        
        if choice == '1':
            tag = input("Enter tag value: ").strip()
            if tag:
                filter_nodes.append({
                    "@class": "viso.model.entities.filters.CustomFilterCondition",
                    "fieldName": {
                        "name": "Tag",
                        "value": "tags.name",
                        "type": "string"
                    },
                    "criteriaOp": "is",
                    "val": tag
                })
                print(f"Added: Tag = '{tag}'")
        
        elif choice == '2':
            firmware = input("Enter firmware version (e.g., V1.1.2): ").strip()
            if firmware:
                filter_nodes.append({
                    "@class": "viso.model.entities.filters.CustomFilterCondition",
                    "fieldName": {
                        "name": "Firmware Version",
                        "value": "deviceSystemInfo.moreData.firmwareInfo.current",
                        "type": "string"
                    },
                    "criteriaOp": "contains",
                    "val": firmware
                })
                print(f"Added: Firmware contains '{firmware}'")
        
        elif choice == '3':
            model = input("Enter model (e.g., TT-8623): ").strip()
            if model:
                filter_nodes.append({
                    "@class": "viso.model.entities.filters.CustomFilterCondition",
                    "fieldName": {
                        "name": "Model",
                        "value": "deviceSystemInfo.systemGeneralInfo.model",
                        "type": "string"
                    },
                    "criteriaOp": "contains",
                    "val": model
                })
                print(f"Added: Model contains '{model}'")
        
        elif choice == '4':
            if not filter_nodes:
                print("No filters added. Using all devices.")
                return None
            break
        
        else:
            print("Invalid choice")
    
    print("\n--- Filter Summary ---")
    for i, node in enumerate(filter_nodes, 1):
        print(f"{i}. {node['fieldName']['name']} contains '{node['val']}'")
    
    return filter_nodes

def send_command(token, device_ids, command_class, command_name):
    """Send a command to multiple devices in batches of 100."""
    url = "https://newline.glbth.com/rest/command/send/sendcommanddatatomany/"
    headers = get_base_headers(token)
    batch_size = 100
    success_count = 0

    for i in range(0, len(device_ids), batch_size):
        batch = device_ids[i:i + batch_size]
        payload = {
            "commandData": {
                "@class": command_class
            },
            "deviceIds": batch
        }
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                if data.get("result") == "SUCCESS":
                    command_id = data.get("data", {}).get("commandid", "N/A")
                    print(f"  {command_name} - SUCCESS (Batch {i//batch_size + 1}, Command ID: {command_id})")
                    success_count += len(batch)
                else:
                    print(f"  {command_name} - FAILED: {data}")
            else:
                print(f"  {command_name} - ERROR: Status {response.status_code}")
        except Exception as e:
            print(f"  {command_name} - ERROR: {str(e)}")

    print(f"\nTotal devices targeted: {success_count}/{len(device_ids)}")
    return success_count == len(device_ids)


def unlock_devices_individually(token, device_ids):
    """Unlock devices one by one."""
    headers = get_base_headers(token)
    payload = {
        "@class": "com.viso.entities.commands.CommandLock",
        "lock_message": None,
        "lock": False
    }
    
    success_count = 0
    
    for device_id in device_ids:
        url = f"https://newline.glbth.com/rest/command/send/sendcommanddata/{device_id}"
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("result") == "SUCCESS":
                    success_count += 1
        except:
            pass
        
        time.sleep(0.05)
    
    print(f"  Unlock Owner Profile - SUCCESS ({success_count}/{len(device_ids)} devices)")
    return success_count > 0

def batch_actions(token):
    """Build filter and apply multiple actions."""
    clear_screen()
    print("=== Batch Actions ===\n")
    
    # Step 1: Build filter or use all devices
    use_filter = input("Apply custom filter? (y/n): ").strip().lower()
    
    devices = []
    device_ids = []
    
    if use_filter == 'y':
        filter_nodes = build_filter()
        
        if filter_nodes:
            print("\nFetching filtered devices...")
            devices = get_devices_with_filter(token, filter_nodes)
        else:
            print("\nFetching all devices...")
            devices = get_all_devices(token)
    else:
        print("\nFetching all devices...")
        devices = get_all_devices(token)
    
    if not devices:
        print("No devices found.")
        input("\nPress Enter to return to the main menu...")
        return
    
    device_ids = [d.get("hardwareId") for d in devices if d.get("hardwareId")]
    
    print(f"\nFound {len(device_ids)} devices")
    
    # Step 2: Select actions
    print("\n=== Select Actions to Perform ===")
    print("(Select multiple by entering numbers separated by commas)")
    print("\n1. Restart")
    print("2. Update Firmware")
    print("3. Unlock Owner Profile")
    print("4. Shutdown")
    
    actions_input = input("\nEnter action numbers (e.g., 1,3,2): ").strip()
    
    if not actions_input:
        print("No actions selected.")
        input("\nPress Enter to return to the main menu...")
        return
    
    selected_actions = [a.strip() for a in actions_input.split(',')]
    
    # Step 3: Confirm
    print(f"\n--- Summary ---")
    print(f"Devices: {len(device_ids)}")
    print(f"Actions:")
    
    action_map = {
        '1': ('Restart', 'com.viso.entities.commands.CommandRestartDevice'),
        '2': ('Update Firmware', 'com.viso.entities.commands.CommandOTAFirmwareUpdate'),
        '3': ('Unlock Owner Profile', None),
        '4': ('Shutdown', 'com.viso.entities.commands.CommandShutdownDevice')
    }
    
    for action in selected_actions:
        if action in action_map:
            print(f"  - {action_map[action][0]}")
    
    confirm = input("\nProceed? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        input("\nPress Enter to return to the main menu...")
        return
    
    # Step 4: Execute actions
    print(f"\n=== Executing Actions on {len(device_ids)} Devices ===\n")
    
    for action in selected_actions:
        if action not in action_map:
            continue
        
        action_name, command_class = action_map[action]
        
        if action == '3':  # Unlock requires individual calls
            unlock_devices_individually(token, device_ids)
        else:
            send_command(token, device_ids, command_class, action_name)
        
        time.sleep(0.5)
    
    print("\n=== All Actions Completed ===")
    input("\nPress Enter to return to the main menu...")

def main_menu(token):
    """Display main menu and handle user choices."""
    while True:
        clear_screen()
        print("=" * 40)
        print("      NEWLINE DEVICE MANAGER")
        print("=" * 40)
        print("\n1. Batch Actions (Filter + Multiple Actions)")
        print("2. Exit")
        print("\n" + "=" * 40)
        
        choice = input("\nEnter your choice (1-2): ").strip()

        if choice == '1':
            batch_actions(token)
        elif choice == '2':
            clear_screen()
            print("Exiting... Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1-2.")
            time.sleep(1.5)

if __name__ == "__main__":
    clear_screen()
    print("=" * 40)
    print("   NEWLINE DEVICE MANAGER - STARTUP")
    print("=" * 40)
    print()
    
    bearer_token = get_bearer_token()
    
    if bearer_token:
        main_menu(bearer_token)
    else:
        print("No token provided. Exiting...")
