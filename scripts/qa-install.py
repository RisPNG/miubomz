#!/usr/bin/env python3
"""Operate one disposable, offline installation test through QMP and serial."""
import argparse
import base64
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import time
import uuid


PROJECT = Path(__file__).resolve().parents[1]
WORK = PROJECT / ".build/qa-uefi"


class QMP:
    def __enter__(self):
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.settimeout(15)
        self.socket.connect(str(WORK / "qmp.sock"))
        self.stream = self.socket.makefile("rwb", buffering=0)
        json.loads(self.stream.readline())
        self.command("qmp_capabilities")
        return self

    def __exit__(self, *_):
        self.stream.close()
        self.socket.close()

    def command(self, execute, arguments=None):
        identifier = uuid.uuid4().hex
        request = {"execute": execute, "id": identifier}
        if arguments is not None:
            request["arguments"] = arguments
        self.stream.write(json.dumps(request).encode() + b"\n")
        while True:
            line = self.stream.readline()
            if not line:
                raise RuntimeError("QEMU disconnected")
            response = json.loads(line)
            if response.get("id") == identifier:
                if "error" in response:
                    raise RuntimeError(response["error"])
                return response["return"]


def start(iso, firmware, memory, inputs):
    iso = iso.resolve(strict=True)
    input_arguments = []
    if inputs:
        directory = inputs.resolve(strict=True)
        input_arguments = ["-virtfs", f"local,path={directory},mount_tag=miubomz-inputs,security_model=none,readonly=on"]
    if (WORK / "qmp.sock").exists():
        raise RuntimeError("The disposable QA guest already exists; stop it first")
    WORK.mkdir(parents=True, exist_ok=True)
    disk = WORK / "system.qcow2"
    firmware_arguments = []
    if firmware == "uefi":
        variables = WORK / "OVMF_VARS.fd"
        if not variables.exists():
            shutil.copyfile("/usr/share/OVMF/OVMF_VARS_4M.fd", variables)
        firmware_arguments = [
            "-drive", "if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd",
            "-drive", f"if=pflash,format=raw,file={variables}",
        ]
    if not disk.exists():
        subprocess.run(["qemu-img", "create", "-f", "qcow2", str(disk), "80G"], check=True)
    command = [
        "qemu-system-x86_64", "-name", f"miubomz-offline-{firmware}-qa",
        "-machine", "q35,accel=kvm", "-cpu", "host", "-m", f"{memory}G", "-smp", "4",
        *firmware_arguments,
        "-drive", f"if=virtio,format=qcow2,file={disk}",
        "-drive", f"media=cdrom,readonly=on,file={iso}",
        *input_arguments,
        "-boot", "order=d,menu=on", "-nic", "none", "-vga", "virtio",
        "-device", "qemu-xhci", "-device", "usb-tablet", "-display", "none",
        "-qmp", f"unix:{WORK / 'qmp.sock'},server=on,wait=off",
        "-chardev", f"socket,id=qa-serial,path={WORK / 'serial.sock'},server=on,wait=off,logfile={WORK / 'serial.log'},logappend=on",
        "-serial", "chardev:qa-serial", "-pidfile", str(WORK / "qemu.pid"),
        "-D", str(WORK / "qemu.log"), "-daemonize",
    ]
    subprocess.run(command, check=True)
    (WORK / "launch.json").write_text(json.dumps({"iso": str(iso), "argv": command}, indent=2) + "\n")
    print(json.dumps({"pid": (WORK / "qemu.pid").read_text().strip(), "workspace": str(WORK)}))


def keys(qmp, sequence):
    codes = sequence.split("-")
    qmp.command("input-send-event", {"events": [
        {"type": "key", "data": {"down": True, "key": {"type": "qcode", "data": code}}}
        for code in codes
    ]})
    time.sleep(0.12)
    qmp.command("input-send-event", {"events": [
        {"type": "key", "data": {"down": False, "key": {"type": "qcode", "data": code}}}
        for code in reversed(codes)
    ]})
    time.sleep(0.12)


def send_serial(serial, data):
    for position in range(0, len(data), 128):
        serial.sendall(data[position:position + 128])
        time.sleep(0.02)


def type_text(qmp, text):
    punctuation = {" ": "spc", "-": "minus", "=": "equal", "_": "shift-minus",
                   ":": "shift-semicolon", ";": "semicolon", "/": "slash", ".": "dot",
                   ",": "comma", "'": "apostrophe", '"': "shift-apostrophe", "\\": "backslash",
                   "(": "shift-9", ")": "shift-0", "!": "shift-1", "@": "shift-2",
                   "#": "shift-3", "$": "shift-4", "%": "shift-5", "^": "shift-6",
                   "&": "shift-7", "*": "shift-8", "+": "shift-equal", "?": "shift-slash",
                   "[": "bracket_left", "]": "bracket_right", "\n": "ret"}
    for character in text:
        if character.isascii() and character.isalnum():
            sequence = ("shift-" if character.isupper() else "") + character.lower()
        else:
            sequence = punctuation[character]
        keys(qmp, sequence)


def guest(command, timeout):
    WORK.mkdir(parents=True, exist_ok=True)
    with (WORK / "serial.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with socket.socket(socket.AF_UNIX) as serial:
            serial.settimeout(1)
            serial.connect(str(WORK / "serial.sock"))
            token = "__MIUBOMZ_QA_" + uuid.uuid4().hex
            deadline = time.monotonic() + timeout
            send_serial(serial, ("set +o emacs; set +o vi; PS1= PS2= PROMPT_COMMAND=; "
                                 "export TERM=dumb SYSTEMD_COLORS=0 NO_COLOR=1; stty -echo; "
                                 f"printf '\\n{token}_READY\\n'\n").encode())
            ready = b""
            while time.monotonic() < deadline:
                try:
                    ready += serial.recv(65536)
                except socket.timeout:
                    continue
                if re.search(rb"\r?\n" + token.encode() + rb"_READY\r?\n", ready):
                    break
            else:
                raise TimeoutError("Guest debug shell did not respond")
            encoded = base64.b64encode(command.encode()).decode()
            payload = "\n".join(encoded[position:position + 1024]
                                for position in range(0, len(encoded), 1024))
            wrapped = (f"printf '\\n{token}_BEGIN\\n'\n"
                       f"base64 -d <<'{token}_PAYLOAD' | /bin/bash --noprofile --norc\n"
                       f"{payload}\n{token}_PAYLOAD\n"
                       f"miubomz_qa_status=$?; printf '\\n{token}_END:%s\\n' \"$miubomz_qa_status\"; stty echo\n")
            send_serial(serial, wrapped.encode())
            output = b""
            start_pattern = re.compile(rb"\r?\n" + token.encode() + rb"_BEGIN\r?\n")
            end_pattern = re.compile(rb"\r?\n" + token.encode() + rb"_END:(\d+)\r?\n")
            while time.monotonic() < deadline:
                try:
                    received = serial.recv(65536)
                    if not received:
                        raise RuntimeError("Guest serial console disconnected")
                    output += received
                except socket.timeout:
                    continue
                begin = start_pattern.search(output)
                end = end_pattern.search(output)
                if begin and end:
                    result = output[begin.end():end.start()].decode(errors="replace").replace("\r\n", "\n")
                    print(result, end="\n" if result and not result.endswith("\n") else "")
                    transcript = {"command": command, "exit": int(end[1]), "output": result}
                    with (WORK / "commands.jsonl").open("a") as record:
                        record.write(json.dumps(transcript) + "\n")
                    return int(end[1])
            serial.sendall(b"\x03")
            raise TimeoutError(f"Guest command did not complete in {timeout} seconds")


def stop():
    try:
        with QMP() as qmp:
            qmp.command("quit")
    except (FileNotFoundError, ConnectionRefusedError):
        pass
    pid_file = WORK / "qemu.pid"
    if pid_file.exists():
        pid = int(pid_file.read_text())
        command = Path(f"/proc/{pid}/cmdline")
        if command.exists() and str(WORK / "qmp.sock").encode() in command.read_bytes():
            os.kill(pid, signal.SIGTERM)
    for path in (WORK / "qmp.sock", WORK / "serial.sock", pid_file):
        path.unlink(missing_ok=True)


def main():
    global WORK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=WORK)
    commands = parser.add_subparsers(dest="command", required=True)
    launch = commands.add_parser("start")
    launch.add_argument("--iso", type=Path, default=PROJECT / "artifacts/miubomz-0.1.0-amd64.iso")
    launch.add_argument("--inputs-dir", type=Path, help="Read-only offline test packages shared through native 9p")
    launch.add_argument("--firmware", choices=("uefi", "bios"), default="uefi")
    launch.add_argument("--memory-gib", type=int, choices=(4, 6), default=6)
    commands.add_parser("status")
    screenshot = commands.add_parser("screenshot")
    screenshot.add_argument("filename", nargs="?", default="screen.png")
    key = commands.add_parser("key")
    key.add_argument("sequence")
    text = commands.add_parser("type")
    text.add_argument("text")
    click = commands.add_parser("click")
    click.add_argument("x", type=int)
    click.add_argument("y", type=int)
    click.add_argument("--width", type=int, default=1280)
    click.add_argument("--height", type=int, default=800)
    shell = commands.add_parser("guest")
    shell.add_argument("script", nargs="?")
    shell.add_argument("--file", type=Path)
    shell.add_argument("--timeout", type=int, default=30)
    commands.add_parser("eject")
    commands.add_parser("stop")
    arguments = parser.parse_args()
    WORK = arguments.work_dir.resolve()
    if arguments.command == "start":
        start(arguments.iso, arguments.firmware, arguments.memory_gib, arguments.inputs_dir)
    elif arguments.command == "guest":
        if arguments.file:
            script = arguments.file.read_text()
        elif arguments.script is not None:
            script = arguments.script
        else:
            parser.error("guest requires a script or --file")
        raise SystemExit(guest(script, arguments.timeout))
    elif arguments.command == "stop":
        stop()
    else:
        with QMP() as qmp:
            if arguments.command == "status":
                print(json.dumps(qmp.command("query-status")))
            elif arguments.command == "screenshot":
                destination = WORK / Path(arguments.filename).name
                qmp.command("screendump", {"filename": str(destination), "format": "png"})
                print(destination)
            elif arguments.command == "key":
                keys(qmp, arguments.sequence)
            elif arguments.command == "type":
                type_text(qmp, arguments.text)
            elif arguments.command == "click":
                qmp.command("input-send-event", {"events": [
                    {"type": "abs", "data": {"axis": "x", "value": arguments.x * 32767 // arguments.width}},
                    {"type": "abs", "data": {"axis": "y", "value": arguments.y * 32767 // arguments.height}},
                ]})
                time.sleep(0.1)
                qmp.command("input-send-event", {"events": [
                    {"type": "btn", "data": {"down": True, "button": "left"}},
                ]})
                time.sleep(0.08)
                qmp.command("input-send-event", {"events": [
                    {"type": "btn", "data": {"down": False, "button": "left"}},
                ]})
                time.sleep(0.25)
            elif arguments.command == "eject":
                drive = next(block["device"] for block in qmp.command("query-block")
                             if block.get("removable") and block.get("inserted"))
                qmp.command("eject", {"device": drive, "force": True})


if __name__ == "__main__":
    main()
