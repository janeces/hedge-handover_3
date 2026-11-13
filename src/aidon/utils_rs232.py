import serial
import time


AIDON_HAN_PORT = '/dev/ttymxc2'
AIDON_HAN_BAUDRATE = 115200


def init_rs232_communication(port=AIDON_HAN_PORT, baudrate=AIDON_HAN_BAUDRATE):
    ser = serial.Serial(
        port=port,
        baudrate=baudrate,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
    )
    return ser


def write_command(ser: serial.Serial, command):
    if not ser.is_open:
        ser.open()

    ser.reset_input_buffer()
    ser.reset_output_buffer()
    payload = command + '\r\n'
    ser.write(payload.encode('utf-8'))
    ser.flush()


def read_response(ser: serial.Serial, sleep_time=0.1):
    time.sleep(sleep_time)
    msg = ser.read(255)
    if ser.is_open:
        ser.close()
    return msg.decode('utf-8', errors='replace')


def read_response_1(ser: serial.Serial, sleep_time=0.1):
    time.sleep(sleep_time)
    available = ser.in_waiting if hasattr(ser, 'in_waiting') else 255
    msg = ser.read(available if available > 0 else 255)
    return msg.decode('utf-8', errors='replace')
