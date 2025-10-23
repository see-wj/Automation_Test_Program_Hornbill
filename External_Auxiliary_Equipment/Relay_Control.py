import pyvisa

class RelayController_Voltage:
    def __init__(self):
        rm = pyvisa.ResourceManager()
        self.relay_device = rm.open_resource("USB0::0x2A8D::0x8F01::CN60460015::0::INSTR")
        self.relay_device.write("*RST")  # optional reset

    def relay_on(self):
        """Activate the relay by turning ON PSU channel 2 at 12 V, 1 A."""
        try:
            self.relay_device.write("INST:NSEL 3")          # Select channel 3
            self.relay_device.write("VOLT 12")              # Set 12 V
            self.relay_device.write("CURR 1")               # Limit to 1 A
            self.relay_device.write("OUTP ON")              # Turn output ON
            print("Relay activated: 12 V applied to coil.")
        except Exception as e:
            print(f"Error activating relay: {e}")

    def relay_off(self):
        """Deactivate the relay by turning OFF PSU channel 2."""
        try:
            self.relay_device.write("INST:NSEL 3")
            self.relay_device.write("OUTP OFF")
            print("Relay deactivated: coil power removed.")
        except Exception as e:
            print(f"Error deactivating relay: {e}")

class RelayController_Current:
    def __init__(self):
        rm = pyvisa.ResourceManager()
        self.relay_device = rm.open_resource("USB0::0x2A8D::0x8F01::CN60460015::0::INSTR")
        self.relay_device.write("*RST")  # optional reset

    def relay_on(self):
        """Activate the relay by turning ON PSU channel 2 at 12 V, 1 A."""
        try:
            self.relay_device.write("INST:NSEL 2")          # Select channel 3
            self.relay_device.write("VOLT 12")              # Set 12 V
            self.relay_device.write("CURR 1")               # Limit to 1 A
            self.relay_device.write("OUTP ON")              # Turn output ON
            print("Relay activated: 12 V applied to coil.")
        except Exception as e:
            print(f"Error activating relay: {e}")

    def relay_off(self):
        """Deactivate the relay by turning OFF PSU channel 2."""
        try:
            self.relay_device.write("INST:NSEL 2")
            self.relay_device.write("OUTP OFF")
            print("Relay deactivated: coil power removed.")
        except Exception as e:
            print(f"Error deactivating relay: {e}")

# Example usage
if __name__ == "__main__":
    relay_voltage = RelayController_Voltage()
    relay_voltage.relay_on()
    relay_current = RelayController_Currrent()
    relay_current.relay_on()
    input("Press Enter to deactivate relay...")
    relay_voltage.relay_off()
    relay_current.relay_off()

