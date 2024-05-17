import pyModbusTCP
import threading
from pyModbusTCP.client import ModbusClient
from pymodbus.exceptions import ConnectionException
import time
import json
import re

STATE_FILE = "last_state.json"

# Function to connect to Modbus client with error handling
def connect_modbus_client(ip, port):
    try:
        client = ModbusClient(ip, port)
        return client
    except ConnectionException as e:
        print(f"An error occurred during connection: {e}")
        return None

# Function to read discrete inputs from Modbus device
def read_discrete_inputs(client, address, count):
    response = client.read_discrete_inputs(address, count)
    return response

# Function to write multiple coils to Modbus device
def write_multiple_coils(client, address, values):
    client.write_multiple_coils(address, values)

# Function to print current settings
def print_settings(ip, port, inputs):
    print("IP Address:", ip)
    print("Port:", port)
    print("Bit States:", inputs)

# Function to continuously write back initial inputs every 0.4 seconds
def continuous_write_back(client, address, inputs):
    while True:
        write_multiple_coils(client, address, inputs)
        time.sleep(0.4)

# Function to change IP address
def change_ip(ip):
    new_ip = input("Enter new IP address: ")
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?$", new_ip):
            return new_ip
    else:
        print("Invalid IP address format. Please try again.")
        change_ip(ip)

# Function to change port
def change_port(port):
    new_port = input("Enter new port: ")
    return int(new_port)

# Function to set enable/disable
def set_enable(inputs):
    enable_value = int(input("Enter 1 to enable or 0 to not: "))
    inputs[0] = enable_value
    return inputs

# Function to set clockwise
def set_cw(inputs):
    cw_value = int(input("Enter 1 to set clockwise or 0 to not: "))
    inputs[1] = cw_value
    return inputs

# Function to set counterclockwise
def set_ccw(inputs):
    ccw_value = int(input("Enter 1 to counterclockwise or 0 to not: "))
    inputs[2] = ccw_value
    return inputs

# Function to change program selection
def change_program_selection(inputs):
    new_selection = int(input("Enter new program selection (0-15): "))
    # Convert selection to binary and pad with zeros
    binary_selection = format(new_selection, '04b')
    inputs[4:8] = [int(bit) for bit in binary_selection]
    return inputs

# Function to save state to file
def save_state(ip, port, inputs):
    state = {
        "ip": ip,
        "port": port,
        "inputs": inputs
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# Function to load state from file
def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        return state["ip"], state["port"], state["inputs"]
    except FileNotFoundError:
        return None, None, None

# Function to load last state and update inputs
def load_last_state():
    last_ip, last_port, last_inputs = load_state()
    if last_ip is not None and last_port is not None and last_inputs is not None:
        return last_ip, last_port, last_inputs
    else:
        print("No previous state found.")
        return None, None, None
    
# Function to update inputs list with 8-bit user input
def bits_input(inputs):
    while True:
        bits = input("Enter up to 8 bits (0s and 1s): ")
        if len(bits) <= 8 and all(bit in '01' for bit in bits):
            inputs[:len(bits)] = [int(bit) for bit in bits]
            inputs[len(bits):8] = [0] * (8 - len(bits))
            break
        else:
            print("Invalid input. Please enter up to 8 bits (0s and 1s).")
    return inputs

# Main function
def main():
    # Load last state
    last_ip, last_port, last_inputs = load_state()

    if last_ip is not None:
        print("\nLast Status:")
        print_settings(last_ip, last_port, last_inputs)

    # Modbus server settings
    default_ip = '192.168.88.254'
    default_port = 502
    ip = last_ip or default_ip
    port = last_port or default_port

    # Connect to Modbus server
    try:
        client = connect_modbus_client(str(ip), port)
        print("Connected to Modbus server.")
    except ConnectionException as e:
        print(e)
        print("Using default IP address and port.")
        ip, port = default_ip, default_port
        client = connect_modbus_client(ip, port)

    ## Connect to Modbus server
    #client = connect_modbus_client(ip, port)
#
    ## If connection fails, revert to previous IP address and port
    #if client is None:
    #    ip, port = last_ip, last_port
    #    client = connect_modbus_client(ip, port)

    # Read initial discrete inputs
    initial_inputs = read_discrete_inputs(client, 0, 8)
    inputs = [int(bit) for bit in initial_inputs]  # Convert to 0/1

    # Initial settings
    print("\nStartup Status:")
    print_settings(ip, port, inputs)

    # Start continuous writing back of initial inputs
    write_thread = threading.Thread(target=continuous_write_back, args=(client, 0, inputs))
    write_thread.daemon = True
    write_thread.start()

    while True:
        # List of commands
        commands = {
            "load_last_state": load_last_state,
            "change_ip": change_ip,
            "change_port": change_port,
            "set_enable": set_enable,
            "change_program_selection": change_program_selection,
            "set_cw": set_cw,
            "set_ccw": set_ccw,
            "bits_input": bits_input,
        }

        # Display available commands
        print("\nAvailable commands:")
        for idx, command in enumerate(commands.keys(), 1):
            print(f"{idx}. {command}")

        # Get user choice
        choice = int(input("Enter command number: "))

        # Execute chosen command
        command_name = list(commands.keys())[choice - 1]

        if command_name == "change_ip":
            new_value = commands[command_name](ip)
            ip = new_value
            client.close()
            client = connect_modbus_client(str(ip), port)
            if client is None:
                ip = default_ip
                client = connect_modbus_client(ip, port)
        elif command_name == "change_port":
            new_value = commands[command_name](port)
            port = new_value
            client.close()
            client = connect_modbus_client(str(ip), port)
            if client is None:
                port = default_port
                client = connect_modbus_client(ip, port)
        elif command_name == "load_last_state":
            new_ip, new_port, new_inputs = commands[command_name]()
            if new_ip and new_port and new_inputs:
                ip = new_ip
                port = new_port
                inputs[:] = new_inputs
                client.close()  # Close existing connection
                client = connect_modbus_client(str(ip), port)  # Reconnect with new IP and port
                print("State loaded successfully.")
        else:
            inputs = commands[command_name](inputs)

        # Print updated settings and discrete inputs
        print("\nCurrent Status:")
        print_settings(ip, port, inputs)

        save_state(ip, port, inputs)

    # Close connection
    client.close()

if __name__ == "__main__":
    main()
