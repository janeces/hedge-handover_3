import serial

ser = serial.Serial(
    port="/dev/ttymxc3",   # or COMx on Windows
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1
)

ser.write(b"ATI\r\n")
resp = ser.read(256)
print(resp.decode(errors="ignore"))