import paramiko
import toml
import os
from cryptography.fernet import Fernet
import sqlite3
import configparser
import getpass

directory = './config'
if not os.path.exists(directory):
    os.makedirs(directory)
    print(f"Directory '{directory}' created.")

conn = sqlite3.connect('./config/user_data.db')
cursor = conn.cursor()

# Tabelle erstellen, falls sie nicht existiert
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    board_id TEXT NOT NULL,
    api_key TEXT NOT NULL
)
''')

conn.commit()
conn.close()


def insert_user_data(username, board_id, api_key):
    conn = sqlite3.connect('./config/user_data.db')
    cursor = conn.cursor()

    # Überprüfe, ob der Benutzer bereits existiert
    cursor.execute('''
    SELECT * FROM user_data WHERE username = ?
    ''', (username,))
    user = cursor.fetchone()

    if user is None:
        # Benutzer existiert nicht, füge neuen Eintrag hinzu
        cursor.execute('''
        INSERT INTO user_data (username, board_id, api_key)
        VALUES (?, ?, ?)
        ''', (username, board_id, api_key))
        conn.commit()
        print(f"Benutzer '{username}' zur Datenbank hinzugefügt.")
    else:
        print(f"Benutzer '{username}' existiert bereits in der Datenbank.")

    conn.close()


def list_users():
    conn = sqlite3.connect('./config/user_data.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT username FROM user_data
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]


def download_file_via_ssh(hostname, port, username, password, remote_path, local_path):
    try:
        # Create an SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the remote server
        ssh.connect(hostname, port, username, password)

        # Use SFTP to download the file
        sftp = ssh.open_sftp()
        sftp.get(remote_path, local_path)

        # Close the SFTP session and SSH connection
        sftp.close()
        ssh.close()

        # print(f"File downloaded successfully from {
        #      remote_path} to {local_path}")
    except Exception as e:
        print(f"An error occurred: {e}")


def upload_file_via_ssh(hostname, port, username, password, local_path, remote_path):
    try:
        # Create an SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the remote server
        ssh.connect(hostname, port, username, password)

        # Use SFTP to upload the file
        sftp = ssh.open_sftp()
        sftp.put(local_path, remote_path)

        # Close the SFTP session and SSH connection
        sftp.close()
        ssh.close()

        # print(f"File uploaded successfully from {local_path} to {remote_path}")
    except Exception as e:
        print(f"An error occurred: {e}")


def restart_service_via_ssh(hostname, port, username, password, service_name):
    try:
        # Create an SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the remote server
        ssh.connect(hostname, port, username, password)

        # Execute the command to restart the service with sudo
        command = f'echo {password} | sudo -S systemctl restart {service_name}'
        stdin, stdout, stderr = ssh.exec_command(command)
        # Wait for the command to complete
        exit_status = stdout.channel.recv_exit_status()

        if exit_status == 0:
            print(f"Service '{service_name}' restarted successfully.")
        else:
            print(f"Failed to restart service '{
                  service_name}'. Error: {stderr.read().decode()}")

        # Close the SSH connection
        ssh.close()
    except Exception as e:
        print(f"An error occurred: {e}")


def find_remote_file(ssh, filename, search_path, exclude_dirs=None):
    try:
        exclude_dirs = exclude_dirs or []
        exclude_cmd = ' '.join(
            [f"-path {os.path.join(search_path, d)} -prune -o" for d in exclude_dirs])
        command = f'find {search_path} {exclude_cmd} -name {filename} -print'
        stdin, stdout, stderr = ssh.exec_command(command)
        result = stdout.read().decode().strip()
        if result:
            return result
        else:
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def update_toml_file(file_path, section, updates, new_file):
    try:
        # Lade die bestehende TOML-Datei
        with open(file_path, 'r') as file:
            config = toml.load(file)

        # Aktualisiere den gewünschten Parameter
        if section in config:
            for key, new_value in updates.items():
                if key in config[section]:
                    config[section][key] = new_value
                else:
                    print(f"Key '{key}' not found in section '{section}'")
        else:
            print(f"Section '{section}' not found in the TOML file.")
            return

        # Schreibe die Änderungen zurück in die TOML-Datei
        with open(new_file, 'w') as file:
            toml.dump(config, file, encoder=toml.TomlPreserveInlineDictEncoder())
        # Ersetze doppelte Anführungszeichen durch einfache Anführungszeichen
        with open(new_file, 'r') as file:
            content = file.read()
        content = content.replace('"', "'")
        with open(new_file, 'w') as file:
            file.write(content)

        # print(f"Parameters in section '{section}' updated in {new_file}")
    except Exception as e:
        print(f"An error occurred: {e}")


def update_ini_file(file_path, section, option, new_value, new_config_file):
    config = configparser.ConfigParser()
    config.read(file_path)

    if section not in config:
        config.add_section(section)

    config[section][option] = new_value

    with open(new_config_file, 'w') as configfile:
        config.write(configfile)


def encrypt_password(password, key):
    cipher_suite = Fernet(key)
    encrypted_password = cipher_suite.encrypt(password.encode()).decode()
    return encrypted_password


def decrypt_password(encrypted_password, key):
    cipher_suite = Fernet(key)
    decrypted_password = cipher_suite.decrypt(
        encrypted_password.encode()).decode()
    return decrypted_password


def clear_screen():
    os.system('clear')


def show_menu():
    clear_screen()
    print(f"""
===========================================
              [{board_name}]
        AUTODARTS PROFILE SWITCHER
===========================================
""")


if not os.path.exists('./config/key.key'):
    key = Fernet.generate_key()
    with open('./config/key.key', 'wb') as file:
        file.write(key)
else:
    with open('./config/key.key', 'rb') as file:
        key = file.read()

cipher_suite = Fernet(key)

# Load configuration from a TOML file
config_file = './config/config.toml'

if not os.path.exists(config_file):
    board_name = ""
    clear_screen()
    show_menu()
    print("Konfigurationsdatei nicht gefunden. Bitte gebe die erforderlichen Informationen ein.")
    print("")
    board_name = input("Name des Boards: ")
    hostname = input("SSH Host: ")
    port = input("SSH Port [22]: ")
    port = int(port) if port else 22
    username = input("SSH Benutzer: ")
    password = getpass.getpass("SSH Passwort: ")
    autodarts_config = f'/home/{username}/.config/autodarts/config.toml'
    remote_path = input(
        f"Entfernte Autodarts-Config: [{autodarts_config}] ") or autodarts_config
    local_path = input("Lokale Config [./config_org.toml]: ")
    local_path = local_path if local_path else './config_org.toml'
    aktueller_benutzer = input(
        "Unter welchem Namen soll der aktuelle Benutzer in der DB abgelegt werden?: ")

    # Encrypt the password
    encrypted_password = encrypt_password(password, key)

    clear_screen()
    show_menu()
    print("Soll der Autodarts-Browser konfiguriert werden?")
    print("")
    choice = input("Ja/Nein [Ja]: ") or 'ja'
    choice = choice.strip().lower()
    if choice == 'nein' or choice == 'no' or choice == 'n' or choice == 'j':
        browser_path = None
    else:
        clear_screen()
        show_menu()
        print("Befindet sich der Autodarts-Browser auf dem selben Host?")
        print("")
        choice = input("Ja/Nein [Ja]: ") or 'ja'
        choice = choice.strip().lower()
        same_host = True
        exclude_dirs = ['.cache', '.config', '.local']
        if choice == 'ja' or choice == 'yes' or choice == 'y' or choice == 'j':
            # Create an SSH client to check for the remote file
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname, port, username, password)
            # Überprüfe, ob die Datei "darts-browser.py" irgendwo im Home-Verzeichnis des SSH-Benutzers vorhanden ist

            browser_path = find_remote_file(
                ssh, 'darts-browser.py', '/home/' + username, exclude_dirs)
            if browser_path:
                browser_dir = os.path.dirname(browser_path)
                browser_config = browser_dir + '/config.ini'
                clear_screen()
                show_menu()
                print(
                    f"Der Autodarts-Browser wurde in {browser_dir} gefunden: ")
                print("")
                browser_config = input(
                    f"Drücke Enter um, [{browser_config}] zu verwenden: ") or browser_config
                same_host = True
            else:
                clear_screen()
                show_menu()
                print("Autodarts-Browser wurde nicht gefunden.")
                print("")
                manual_config = input(
                    "Möchten Sie die Browser-Konfiguration manuell eingeben? (ja/nein): ").strip().lower()
                if manual_config == 'ja' or manual_config == 'yes' or manual_config == 'y' or manual_config == 'j':
                    browser_path = input("Pfad zum Autodarts-Browser: ")
                    same_host = True
                else:
                    print("Überspringe Browser-Konfiguration.")
                    browser_path = None
        else:
            browser_hostname = input("SSH Host für Browser: ")
            browser_port = input("SSH Port [22]: ") or '22'
            browser_username = input("SSH Benutzer für Browser: ")
            browser_password = getpass.getpass("SSH Passwort für Browser: ")
            encrypted_browser_password = encrypt_password(
                browser_password, key)
            browser_ssh = paramiko.SSHClient()
            browser_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            browser_ssh.connect(browser_hostname, int(port),
                                browser_username, browser_password)
            browser_path = find_remote_file(
                browser_ssh, 'darts-browser.py', '/home/' + browser_username, exclude_dirs)
            same_host = False
            print("Noch nicht implementiert.")
            browser_path = None

    # Füge Browser-Konfiguration hinzu, falls vorhanden
    if browser_path:
        if same_host:
            config = {
                'general': {
                    'board_name': board_name
                },
                'browser': {
                    'same_host': same_host,
                    'path': browser_config,
                    'local_browser_config': './config_browser_org.ini'
                },
                'ssh': {
                    'hostname': hostname,
                    'port': port,
                    'username': username,
                    'password': encrypted_password,
                    'remote_path': remote_path,
                    'local_path': local_path
                }
            }
        else:

            config = {
                'general': {
                    'board_name': board_name
                },
                'browser': {
                    'same_host': same_host,
                    'ssh': {
                        'hostname': browser_hostname,
                        'port': browser_port,
                        'username': browser_username,
                        'password': encrypted_browser_password
                    },
                    'path': browser_config,
                    'local_browser_config': './config_browser_org.ini'
                },
                'ssh': {
                    'hostname': hostname,
                    'port': port,
                    'username': username,
                    'password': encrypted_password,
                    'remote_path': remote_path,
                    'local_path': local_path
                }
            }
    else:
        config = {
            'general': {
                'board_name': board_name
            },
            'ssh': {
                'hostname': hostname,
                'port': port,
                'username': username,
                'password': encrypted_password,
                'remote_path': remote_path,
                'local_path': local_path
            }
        }
    # Write the config to the TOML file
    with open(config_file, 'w') as file:
        toml.dump(config, file)

    download_file_via_ssh(hostname, port, username,
                          password, remote_path, local_path)

    # Lese die heruntergeladene Konfigurationsdatei
    with open(local_path, 'r') as file:
        downloaded_config = toml.load(file)

    # Extrahiere board_id und api_key und füge sie in die Datenbank ein
    board_id = downloaded_config['auth']['board_id']
    api_key = downloaded_config['auth']['api_key']
    insert_user_data(aktueller_benutzer, board_id, api_key)

else:
    with open(config_file, 'r') as file:
        config = toml.load(file)

board_name = str(config['general']['board_name'])
hostname = str(config['ssh']['hostname'])
port = int(config['ssh']['port'])
username = str(config['ssh']['username'])
remote_path = str(config['ssh']['remote_path'])
local_path = str(config['ssh']['local_path'])

# Decrypt the password
encrypted_password_from_config = config['ssh']['password']
password = decrypt_password(encrypted_password_from_config, key)

browser_installed = False
if 'browser' in config:
    browser_path = str(config['browser']['path'])
    local_browser_config = str(config['browser']['local_browser_config'])
    browser_installed = True


def get_user_data(username):
    conn = sqlite3.connect('./config/user_data.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT board_id, api_key FROM user_data WHERE username = ?
    ''', (username,))
    rows = cursor.fetchall()
    conn.close()
    return rows


# Menüführung beim Programmstart
while True:
    clear_screen()
    show_menu()
    print("1. Neuen Benutzer anlegen")
    print("2. Vorhandenen Benutzer auswählen")
    print("")
    choice = input("Wähle eine Option (1 oder 2): ")

    if choice == '1':
        clear_screen()
        show_menu()
        user = input("Benutzer: ")
        board_id = input("Board ID: ")
        api_key = input("API key: ")
        insert_user_data(user, board_id, api_key)
        break
    elif choice == '2':
        clear_screen()
        show_menu()
        users = list_users()
        if not users:
            print(
                "Keine Benutzer in der Datenbank vorhanden. Bitte legen Sie einen neuen Benutzer an.")
            user = input("Benutzer: ")
            board_id = input("Board ID: ")
            api_key = input("API key: ")
            insert_user_data(user, board_id, api_key)
        else:
            print("Vorhandene Benutzer:")
            print("===================")
            for i, user in enumerate(users, start=1):
                print(f"{i}. {user}")
            print("")
            user_choice = int(input("Wähle einen Benutzer (Nummer): "))
            user = users[user_choice - 1]
        break
    else:
        print("Ungültige Option. Bitte versuchen Sie es erneut.")
        input("Drücken Sie die Eingabetaste, um fortzufahren...")

user_data = get_user_data(user)
# print(user_data)

# Wähle einen Eintrag aus
selected_board_id, selected_api_key = user_data[0]
new_file = f'./config_{user}.toml'
# Schreibe die ausgewählten Werte in die Konfigurationsdatei
updates = {
    'board_id': selected_board_id,
    'api_key': selected_api_key
}


download_file_via_ssh(hostname, port, username,
                      password, remote_path, local_path)
update_toml_file('config_org.toml', 'auth', updates, new_file)
# Lade die aktualisierte Konfigurationsdatei per SSH hoch
upload_file_via_ssh(hostname, port, username, password, new_file, remote_path)

# Neustarten von autodarts
service_name = 'autodarts'
restart_service_via_ssh(hostname, port, username, password, service_name)

if browser_installed:
    browser_choice = input("Browserfenster oben oder unten? (1/2)[1]: ")
    if browser_choice == '1':
        browser = "board1_id"
    elif browser_choice == '2':
        browser = "board2_id"
    else:
        browser = "board1_id"
    new_browser_config = f'./config_browser_{user}.ini'
    download_file_via_ssh(hostname, port, username,
                          password, browser_path, local_browser_config)
    # Ändere den Wert in der INI-Datei
    update_ini_file(local_browser_config, 'boards', browser,
                    updates['board_id'], new_browser_config)
    # Lade die aktualisierte INI-Datei wieder hoch
    upload_file_via_ssh(hostname, port, username, password,
                        new_browser_config, browser_path)
