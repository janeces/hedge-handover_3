# import paho.mqtt.client as mqtt_client
#
# client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2)
# client.username_pw_set("ijs-hedgeiot", "mqTT5stefan")
# client.tls_set(ca_certs="certificate/operato-mqttca.crt")
# # client.tls_insecure_set(True)
# topic = "Operato/Trafoflex/MC705A"
#
# def on_connect(client, userdata, flags, rc, properties):
#     if rc == mqtt_client.CONNACK_ACCEPTED:
#         print(f"Subscribing to topic {topic}")
#         client.subscribe(topic)
#     else:
#         print(f"Connection failed with code {rc}")
#
#
# def on_message(client, userdata, msg):
#     print(f"Got message \n>{msg.payload.decode()}<")
#
# client.on_connect = on_connect
# client.on_message = on_message
#
# client.connect("sumo.operato.eu", 1883)
#
# client.loop_forever()
# print("Loop started")

# -----------------------------------------------
import device_io.trafoflex.pb2 as pb

model = pb.TransformerModel()

models = ["6004-RP_KOKRA", "6001-TP_ŽELEZNO"]

with open(f"models/{models[1]}.pb", "rb") as f:
    model.ParseFromString(f.read())

print(model)
