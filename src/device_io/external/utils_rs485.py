import serial.rs485
import time


def init_rs485_communication():
    """Creates the RS485 communication object"""
    # baud rate old = 9600
    ser = serial.rs485.RS485(port='/dev/ttymxc3', baudrate=19200, bytesize=8, parity='N', stopbits=1, timeout=1,
                             rtscts=False, dsrdtr=False)
    ser.rs485_mode = serial.rs485.RS485Settings(False, False)
    return ser


def write_command(ser: serial.rs485.RS485, command):
    """Writes a command to the serial port
    :param ser: serial port
    :param command: command to write"""
    #ser.flush()
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    ser.flush()  # Makes more sense to flush here.
    comm = command + '\r\n'
    ser.write(comm.encode('utf-8'))


def read_response(ser: serial.rs485.RS485, sleep_time=0.1):
    time.sleep(sleep_time)
    msg = ser.read(255)
    ser.close()
    return msg.decode()


def read_response_1(ser: serial.rs485.RS485, sleep_time=0.1):
    """Reads a response from the serial port
    :param ser: serial port
    :param sleep_time: sleep time in seconds before reading the response"""
    time.sleep(sleep_time)
    msg = ser.read(ser.in_waiting)
    return msg.decode()
