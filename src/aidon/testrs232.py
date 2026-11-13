#!/usr/bin/env python3

import argparse
import sys
import time

from utils_rs232 import init_rs232_communication


def main():
    parser = argparse.ArgumentParser(description='Listen on the Aidon HAN RS232 port and print incoming data.')
    parser.add_argument('--port', default='/dev/ttymxc2', help='Aidon HAN serial device path (default: /dev/ttymxc2)')
    parser.add_argument('--baudrate', type=int, default=115200, help='Serial baud rate (default: 115200; Aidon HAN uses 8N1)')
    parser.add_argument('--timeout', type=float, default=1.0, help='Read timeout in seconds (default: 1.0)')
    parser.add_argument('--mode', choices=['hex', 'text'], default='hex', help='Display mode: hex for raw binary, text for best-effort ASCII')
    args = parser.parse_args()

    try:
        ser = init_rs232_communication(port=args.port, baudrate=args.baudrate)
        ser.timeout = args.timeout
        ser.inverted = True  # Ensure the serial port is not inverted
        print(f'Listening on {args.port} at {args.baudrate} baud in {args.mode} mode. Press Ctrl+C to stop.')

        while True:
            data = ser.read(256)
            if not data:
                continue

            if args.mode == 'hex':
                print(f'[{time.strftime("%H:%M:%S")}] {data.hex(" ")}', end='')
            else:
                try:
                    text = data.decode('utf-8')
                except UnicodeDecodeError:
                    text = data.decode('latin-1', errors='replace')
                print(f'[{time.strftime("%H:%M:%S")}] {text}', end='')
            sys.stdout.flush()

    except KeyboardInterrupt:
        print('\nStopping RS232 listener.')
    finally:
        try:
            if 'ser' in locals():
                ser.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()
