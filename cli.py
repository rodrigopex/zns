import os
import subprocess
import argparse
from pathlib import Path
import google.protobuf.text_format as text_format

import sys
sys.path.append(
    f"{os.environ['ZEPHYR_BASE']}/../modules/lib/nanopb/generator/proto")

parser = argparse.ArgumentParser()

subparser = parser.add_subparsers()
parse_decode = subparser.add_parser('decode')
parse_decode.add_argument("decode_type", default='cmd', nargs='?', choices=["cmd", "rsp", "evt"],
                          help='Decode from hexstring to text format (default: %(default)s)')

parse_encode = subparser.add_parser('encode')
parse_encode.add_argument("encode_type", default='cmd', nargs='?', choices=["cmd", "rsp", "evt"],
                          help='Encode from text format to hexstring (default: %(default)s)')

parser.add_argument("proto_file_path")
parser.add_argument("text")

args = parser.parse_args()

proto_file = Path(args.proto_file_path)

if not proto_file.exists():
    print("The target directory doesn't exist")
    raise SystemExit(1)


def generate_python_protobuf_file(service_proto_file: Path):
    """
    Generates the python files used by this script to manipulate the proto messages

    :param services list of string: list with the services names to be used. The name must match
    with the proto file. For example, indicator must have a indicator.proto file inside the
    proto path folder.
    :param services_proto_path the path to the proto files folder: All the proto files must be
    in the same folder for now.
    """
    build_path = Path('build', service_proto_file.parent)
    build_path.mkdir(parents=True, exist_ok=True)

    if not service_proto_file.exists:
        raise AssertionError(
            "Please use a valid proto file name (ex: /home/user/my_protofile.proto)")

    subprocess.run(f"protoc -I{os.environ['ZEPHYR_BASE']}/../modules/lib/nanopb/generator/proto/ --python_out=build/{service_proto_file.parent} nanopb.proto",
                   shell=True, check=True).returncode

    service_py_file_path = Path(
        './build', service_proto_file.parent, f"{service_proto_file.stem}_pb2.py")
    if not service_py_file_path.exists():
        subprocess.run(f"protoc -I{os.environ['ZEPHYR_BASE']}/../modules/lib/nanopb/generator/proto -I. --python_out=build {service_proto_file}",
                       shell=True, check=True).returncode


def load_service(service_name):
    from importlib import util

    spec = util.spec_from_file_location(
        f"{service_name}_pb2", f"./build/nano_services/{service_name}_pb2.py")

    if spec is None:
        raise AssertionError(
            f"Python protobuf message file {service_name}_pb2.py does not exist.")

    service = util.module_from_spec(spec)

    if service is None or spec.loader is None:
        raise AssertionError(
            f"Could not import {service_name}_pb2.py file.")

    spec.loader.exec_module(service)

    return service


def encode(service_name: str, text_format_str, iface: str):
    service = load_service(service_name)

    service_name_title = "".join(x.title()
                                 for x in service_name.lower().split("_"))

    serv_class = getattr(service, service_name_title)

    iface_title = iface.title()
    message_class = getattr(serv_class, f"{iface_title}Msg")

    encoded_message = text_format.Parse(
        text_format_str, message_class()).SerializeToString().hex()
    print(encoded_message.rstrip())


def decode(service_name: str, hex_string, iface: str):
    service = load_service(service_name)

    service_name_title = "".join(x.title()
                                 for x in service_name.lower().split("_"))

    serv_class = getattr(service, service_name_title)

    iface_title = iface.title()
    message_class = getattr(serv_class, f"{iface_title}Msg")
    msg = message_class()
    msg.ParseFromString(bytes.fromhex(hex_string))
    print(repr(msg).rstrip())


if __name__ == "__main__":
    proto_file_path = Path(args.proto_file_path)
    generate_python_protobuf_file(proto_file_path)
    args_keys = vars(args).keys()
    if 'decode_type' in args_keys:
        decode(proto_file_path.stem,  args.text, args.decode_type)
    elif 'encode_type' in args_keys:
        encode(proto_file_path.stem,  args.text, args.encode_type)
