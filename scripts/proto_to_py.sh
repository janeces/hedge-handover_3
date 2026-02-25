#!/bin/bash
# Generates the Python module from the .proto class definition.

#protoSource="/home/hedge_operato/hedge/trafoflex/code/Trafoflex_C++_IJS/src/proto/"
protoSource="/home/hedge_operato/hedge/Dythera/dythera/src/proto/"

echo "${protoSource}dtr.proto --proto_path ${protoSource} --python_out ."

protoc "${protoSource}dtr.proto" --proto_path ${protoSource} --python_out .