import paramiko
import toml
import os
from cryptography.fernet import Fernet
import sqlite3

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
        print(f"User '{username}' added to the database.")
    else:
        print(f"User '{username}' already exists in the database.")

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

        print(f"File downloaded successfully from {
              remote_path} to {local_path}")
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

        print(f"File uploaded successfully from {local_path} to {remote_path}")
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

        print(f"Parameters in section '{section}' updated in {new_file}")
    except Exception as e:
        print(f"An error occurred: {e}")


def encrypt_password(password, key):
    cipher_suite = Fernet(key)
    encrypted_password = cipher_suite.encrypt(password.encode()).decode()
    return encrypted_password


def decrypt_password(encrypted_password, key):
    cipher_suite = Fernet(key)
    decrypted_password = cipher_suite.decrypt(
        encrypted_password.encode()).decode()
    return decrypted_password


directory = './config'
if not os.path.exists(directory):
    os.makedirs(directory)
    print(f"Directory '{directory}' created.")
else:
    print(f"Directory '{directory}' already exists.")

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
    hostname = input("Enter SSH hostname: ")
    port = int(input("Enter SSH port: "))
    username = input("Enter SSH username: ")
    remote_path = input("Enter remote file path: ")
    local_path = input("Enter local file path: ")
    password = input("Enter SSH password: ")

    # Encrypt the password
    encrypted_password = encrypt_password(password, key)

    # Create the config dictionary
    config = {
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
else:
    with open(config_file, 'r') as file:
        config = toml.load(file)

hostname = str(config['ssh']['hostname'])
port = int(config['ssh']['port'])
username = str(config['ssh']['username'])
remote_path = str(config['ssh']['remote_path'])
local_path = str(config['ssh']['local_path'])

# Decrypt the password
encrypted_password_from_config = config['ssh']['password']
password = decrypt_password(encrypted_password_from_config, key)


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
print("1. Neuen Benutzer anlegen")
print("2. Vorhandenen Benutzer auswählen")
choice = input("Wähle eine Option (1 oder 2): ")

if choice == '1':
    user = input("Benutzer: ")
    board_id = input("Board ID: ")
    api_key = input("API key: ")
    insert_user_data(user, board_id, api_key)
elif choice == '2':
    users = list_users()
    if not users:
        print("Keine Benutzer in der Datenbank vorhanden. Bitte legen Sie einen neuen Benutzer an.")
        user = input("Benutzer: ")
        board_id = input("Board ID: ")
        api_key = input("API key: ")
        insert_user_data(user, board_id, api_key)
    else:
        print("Vorhandene Benutzer:")
        for i, user in enumerate(users, start=1):
            print(f"{i}. {user}")
        user_choice = int(input("Wähle einen Benutzer (Nummer): "))
        user = users[user_choice - 1]
else:
    print("Ungültige Option. Programm wird beendet.")
    exit()

user_data = get_user_data(user)
print(user_data)

# Wähle einen Eintrag aus (zum Beispiel den ersten)
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
