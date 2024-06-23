#!/usr/bin/env python3

"""
Run the command `python -m robot.libdoc LibraryNanoServices LibraryNanoServices.libspec` to make the
library available on the robotframework_lsp.
"""

import logging
import google.protobuf.text_format as text_format
import serial

import os
import sys

sys.path.append(f"{os.environ['ZEPHYR_BASE']}/../modules/lib/nanopb/generator/proto")

logger = logging.getLogger(__name__)


class LibraryNanoServices(object):
    def __init__(
        self,
        services=None,
        services_proto_path="",
        port="/dev/ttyACM0",
        baudrate=115200,
        **kwargs,
    ):
        self.service_list = services
        self.service_path = services_proto_path
        self.__generate_python_protobuf_file()
        if "timeout" in kwargs.keys():
            kwargs["timeout"] = int(kwargs["timeout"])
        self.__serial = serial.Serial(port, baudrate, **kwargs)

    def __generate_python_protobuf_file(self):
        """
        Generates the python files used by this script to manipulate the proto messages

        :param services list of string: list with the services names to be used. The name must match
        with the proto file. For example, indicator must have a indicator.proto file inside the
        proto path folder.
        :param services_proto_path the path to the proto files folder: All the proto files must be
        in the same folder for now.
        """
        if self.service_list is None:
            return

        import subprocess

        if (
            subprocess.run(
                f"protoc -I{os.environ['ZEPHYR_BASE']}/../modules/lib/nanopb/generator/proto/ --python_out=build/{self.service_path} nanopb.proto",
                shell=True,
                check=True,
            ).returncode
            != 0
        ):
            raise AssertionError("Could not compile the nanopb proto file")

        sys.path.append(os.path.join(".", "build", str(self.service_path)))

        for service_name in self.service_list:
            service_py_file_path = os.path.join(
                "build", self.service_path, f"{service_name}_pb2.py"
            )
            service_proto_file_path = os.path.join(
                self.service_path, f"{service_name}.proto"
            )
            if not os.path.exists(service_py_file_path):
                subprocess.run(
                    f"protoc -I{os.environ['ZEPHYR_BASE']}/../modules/lib/nanopb/generator/proto -I. --python_out=build {service_proto_file_path}",
                    shell=True,
                    check=True,
                ).returncode

    def cleanup(self):
        self.__serial.close()

    def __load_service(self, service_name):
        from importlib import util

        spec = util.spec_from_file_location(
            f"{service_name}_pb2",
            f"./build/{self.service_path}/{service_name}_pb2.py",
            submodule_search_locations=["./build/include"],
        )

        if spec is None:
            raise AssertionError(
                f"Python protobuf message file {service_name}_pb2.py does not exist."
            )

        service = util.module_from_spec(spec)

        if service is None or spec.loader is None:
            raise AssertionError(f"Could not import {service_name}_pb2.py file.")

        spec.loader.exec_module(service)

        return service

    def service_execute_command(self, service_name: str, **kwargs):
        service = self.__load_service(service_name)

        service_name_title = "Msg" + "".join(
            x.title() for x in service_name.lower().split("_")
        )

        serv_class = getattr(service, service_name_title)
        cmd_message_class = getattr(serv_class, "Cmd")
        rsp_message_class = getattr(serv_class, "Evt")

        print(kwargs)

        encoded_message = (
            text_format.Parse(kwargs["Cmd"], cmd_message_class())
            .SerializeToString()
            .hex()
        )
        print(f"Encoded cmd data: {encoded_message}")
        self.__serial.write(f"{service_name}_cmd {encoded_message}\n".encode())

        data = self.__serial.read_until(expected=b"@")
        data = self.__serial.read_until(expected=b"uart:~$")
        data = data.strip()

        data_list = data.split()

        if len(data_list) < 2:
            raise AssertionError(
                "No responses from the command. Check the command message."
            )

        data = data_list[1].decode("ascii")

        rsp_msg = rsp_message_class()
        rsp_msg.ParseFromString(bytes.fromhex(data))

        expected_rsp_msg = text_format.Parse(kwargs["Evt"], rsp_message_class())

        print(
            f"Cmd in text_format:\n{repr(rsp_msg)}Encoded rsp data: {data}\nRsp in text format:\n{repr(expected_rsp_msg)}"
        )
        if rsp_msg != expected_rsp_msg:
            raise AssertionError(
                f"The result:\n{repr(rsp_msg)}\nis different from the expected:\n\n{repr(expected_rsp_msg)}"
            )
        return True

    def service_wait_for_event(self, service_name: str, **kwargs):
        service = self.__load_service(service_name)

        service_name_title = "Msg" + "".join(
            x.title() for x in service_name.lower().split("_")
        )

        serv_class = getattr(service, service_name_title)
        evt_message_class = getattr(serv_class, "Evt")

        print(kwargs)

        data = self.__serial.read_until(expected=b"@")
        data = self.__serial.read_until(expected=b"uart:~$")
        data = data.strip()

        if data == b"":
            raise AssertionError(
                f"Timeout! No event from {service_name_title} service received."
            )

        data_list = data.strip().split()

        if len(data_list) < 2:
            raise AssertionError(
                "No responses from the command. Check the command message."
            )

        data = data_list[1].decode("ascii")

        evt_msg = evt_message_class()
        evt_msg.ParseFromString(bytes.fromhex(data))

        expected_evt_msg = text_format.Parse(kwargs["Evt"], evt_message_class())

        print(
            f"Evt in text_format:\n{repr(evt_msg)}Encoded evt data: {data}\nEvt in text format:\n{repr(expected_evt_msg)}"
        )
        if evt_msg != expected_evt_msg:
            raise AssertionError(
                f"The result:\n{repr(evt_msg)}\nis different from the expected:\n\n{repr(expected_evt_msg)}"
            )
        return True


if __name__ == "__main__":
    zb_sh = LibraryNanoServices(
        ["indicator", "trigger"], "include", "/dev/tty.usbmodem0004402937221"
    )
    try:
        print(
            zb_sh.service_execute_command(
                "indicator",
                Cmd="on {}",
                Evt="state { on: true }",
            )
        )
        print(
            zb_sh.service_execute_command(
                "indicator",
                Cmd="off {}",
                Evt="state { on: false }",
            )
        )

    except KeyboardInterrupt:
        zb_sh.cleanup()
