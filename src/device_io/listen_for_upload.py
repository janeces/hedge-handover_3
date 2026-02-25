import device_io.io as dio

broker, port, uname, pwd = dio.import_credentials(dio.CREDENTIALS_DIR)

client = dio.MQTTClient(broker, port, dio.UPLOAD_TOPIC, uname, pwd, dio.CERTIFICATE_DIR)


def on_msg(client, userdata, msg):
    print(msg.payload.decode())

client.set_on_message(on_msg)

client.connect()
client.client.loop_forever()

