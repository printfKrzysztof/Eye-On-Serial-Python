import tkinter as tk
from tkinter import ttk
from pyvirtualserial import VirtualSerial
import threading
import serial
import serial.tools.list_ports
import time

RX = "<-- (Rx)"
TX = "--> (Tx)"
class SerialPortMirrorApp:
    def update_checkbox(self):
        if self.enable_format_rx_only.get():
            self.enable_timestamps.set(False)
            self.timestamp_check.config(state=tk.DISABLED)
        else:
            self.timestamp_check.config(state=tk.NORMAL)

    def __init__(self, root):
        self.root = root
        self.root.title("Serial Port Mirror")

        self.baudrate = tk.StringVar(value="115200")
        self.real_port = tk.StringVar()
        self.virtual_port_number = tk.StringVar(value="12")
        self.log_file = tk.StringVar(value="ur_log.txt")
        self.enable_timestamps = tk.BooleanVar(value=False)
        self.enable_format_rx_only = tk.BooleanVar(value=True)
        self.display_hex = tk.BooleanVar(value=True)  # Default to hexadecimal display

        self.running = False  # Flag to track if mirroring is running
        self.start_button = tk.Button(root, text="Start", command=self.toggle_mirroring)
        self.start_button.grid(row=6, column=0, columnspan=2, pady=10)

        # Real port selection
        tk.Label(root, text="Real Port:").grid(row=0, column=0, padx=10, pady=10)
        self.real_port_combo = ttk.Combobox(root, textvariable=self.real_port, values=self.get_serial_ports(), state="readonly")
        self.real_port_combo.grid(row=0, column=1, padx=10, pady=10)

        # Baud rate selection
        tk.Label(root, text="Baud Rate:").grid(row=1, column=0, padx=10, pady=10)
        baudrate_options = ["300", "600", "1200", "2400", "4800", "9600", "14400", "19200", "38400", "57600", "115200"]
        self.baudrate_combo = ttk.Combobox(root, textvariable=self.baudrate, values=baudrate_options, state="readonly")
        self.baudrate_combo.grid(row=1, column=1, padx=10, pady=10)

        # Virtual port number
        tk.Label(root, text="Virtual Port Number:").grid(row=2, column=0, padx=10, pady=10)
        tk.Entry(root, textvariable=self.virtual_port_number).grid(row=2, column=1, padx=10, pady=10)

        # Log file name
        tk.Label(root, text="Log File Name:").grid(row=3, column=0, padx=10, pady=10)
        tk.Entry(root, textvariable=self.log_file).grid(row=3, column=1, padx=10, pady=10)

        # Enable timestamps
        self.timestamp_check = tk.Checkbutton(root, text="Enable Timestamps", variable=self.enable_timestamps)
        self.timestamp_check.grid(row=4, column=0, columnspan=2, pady=10)
        self.timestamp_check.config(state=tk.DISABLED)
        # Format RX Only
        self.format_rx_only = tk.Checkbutton(root, text="RX Stream Mode", variable=self.enable_format_rx_only,command=self.update_checkbox)
        self.format_rx_only.grid(row=5, column=0, columnspan=2, pady=10)

        # Display format
        self.display_format_radio_hex = tk.Radiobutton(root, text="Hexadecimal", variable=self.display_hex, value=True)
        self.display_format_radio_hex.grid(row=7, column=0, padx=10, pady=10)

        self.display_format_radio_ascii = tk.Radiobutton(root, text="ASCII", variable=self.display_hex, value=False)
        self.display_format_radio_ascii.grid(row=7, column=1, padx=10, pady=10)

    def get_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def hex_format(self, data):
        hex_data = ' '.join([f'{byte:02X}' for byte in data])
        return hex_data

    def ascii_format(self, data):
        return data.decode('ascii', errors='ignore')

    def log_data(self, f, direction, data):
        # Data to Hex or Asci
        if self.display_hex.get():
            formatted_data = self.hex_format(data)
        else:
            formatted_data = self.ascii_format(data)        
        
        # Format RX only mode.
        if self.format_rx_only:
            if direction == RX:
                log_entry = f"TX({formatted_data})"
            elif direction == TX:
                log_entry = f"{formatted_data}"
                pass
            else:
                raise Exception("Wrong way - communication!")
        else:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S") if self.enable_timestamps.get() else ""
            log_entry = f"{direction} {timestamp}: {formatted_data}\n"
        
        f.write(log_entry)
        print(log_entry)

    def mirror_and_log_data(self, real_port, baudrate, virtual_port, logfile):
        try:
            ser = serial.Serial(real_port, baudrate, timeout=1)
            vir = serial.Serial(virtual_port, baudrate, timeout=1)
            self.running = True  # Set running flag
            self.start_button.config(text="Stop")  # Change button text to Stop

            with open(logfile, 'a') as f:
                while self.running:  # Continue loop while running flag is True
                    if ser.in_waiting:
                        data = ser.read(ser.in_waiting)
                        self.log_data(f, RX, data)
                        vir.write(data)
            
                    if vir.in_waiting:
                        data = vir.read(vir.in_waiting)
                        self.log_data(f, TX, data)
                        ser.write(data)
                    
        except Exception as e:
            print(f"Error in mirror_and_log_data: {e}")
        finally:
            self.running = False  # Reset running flag
            self.start_button.config(text="Start")  # Change button text back to Start

    def toggle_mirroring(self):
        if self.running:  # If mirroring is running, stop it
            self.running = False
        else:  # If mirroring is not running, start it
            real_port = self.real_port.get()
            baudrate = int(self.baudrate.get())
            logfile = self.log_file.get()
            virtual_port_number = self.virtual_port_number.get()
            virtual_port = f"COM{virtual_port_number}"
            try:
                virtual_serial = VirtualSerial(port=int(virtual_port_number), baudrate=baudrate)
                print(f"Virtual port {virtual_port} created with baud rate {baudrate}")
               
                mirror_thread = threading.Thread(target=self.mirror_and_log_data, args=(real_port, baudrate, virtual_port, logfile))
                mirror_thread.daemon = True
                mirror_thread.start()
            except Exception as e:
                print(f"Error in start_mirroring: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialPortMirrorApp(root)
    root.mainloop()