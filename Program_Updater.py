"""External updater used by the packaged application."""

import argparse
import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from pathlib import Path


def wait_for_process(process_id, timeout=120):
    process_id = int(process_id)
    if process_id <= 0:
        return
    if os.name == "nt":
        synchronize = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(
            synchronize,
            False,
            process_id,
        )
        if handle:
            try:
                ctypes.windll.kernel32.WaitForSingleObject(
                    handle,
                    int(timeout * 1000),
                )
            finally:
                ctypes.windll.kernel32.CloseHandle(handle)
            return
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(process_id, 0)
        except OSError:
            return
        time.sleep(0.25)
    raise TimeoutError("Application did not close before update timeout")


def safe_extract(package_path, destination):
    destination = Path(destination).resolve()
    with zipfile.ZipFile(package_path) as archive:
        for member in archive.infolist():
            member_path = (destination / member.filename).resolve()
            try:
                member_path.relative_to(destination)
            except ValueError as exception:
                raise ValueError(
                    f"Unsafe path in update archive: {member.filename}"
                ) from exception
        archive.extractall(destination)


def locate_payload(extraction_directory, executable):
    extraction_directory = Path(extraction_directory)
    if (extraction_directory / executable).is_file():
        return extraction_directory
    candidates = [
        path.parent
        for path in extraction_directory.rglob(executable)
        if path.is_file()
    ]
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"Update archive must contain exactly one {executable}"
        )
    return candidates[0]


def install_update(package_path, target, executable, preserve_paths=()):
    package_path = Path(package_path).resolve()
    target = Path(target).resolve()
    parent = target.parent
    extraction_directory = Path(
        tempfile.mkdtemp(prefix="automation_update_extract_")
    )
    prepared_directory = parent / f".{target.name}.new-{uuid.uuid4().hex}"
    backup_directory = parent / f"{target.name}.previous"

    try:
        safe_extract(package_path, extraction_directory)
        payload = locate_payload(extraction_directory, executable)
        shutil.copytree(payload, prepared_directory)
        if not (prepared_directory / executable).is_file():
            raise FileNotFoundError(
                f"Prepared update is missing {executable}"
            )

        if backup_directory.exists():
            shutil.rmtree(backup_directory)
        target.rename(backup_directory)
        try:
            prepared_directory.rename(target)
            for relative_path in preserve_paths:
                old_path = backup_directory / relative_path
                new_path = target / relative_path
                if old_path.is_dir():
                    shutil.copytree(old_path, new_path, dirs_exist_ok=True)
                elif old_path.is_file():
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(old_path, new_path)
            if not (target / executable).is_file():
                raise FileNotFoundError(
                    f"Installed update is missing {executable}"
                )
        except Exception:
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
            backup_directory.rename(target)
            raise
        return backup_directory
    finally:
        shutil.rmtree(extraction_directory, ignore_errors=True)
        if prepared_directory.exists():
            shutil.rmtree(prepared_directory, ignore_errors=True)


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--executable", required=True)
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--preserve", action="append", default=[])
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    wait_for_process(arguments.pid)
    install_update(
        arguments.package,
        arguments.target,
        arguments.executable,
        arguments.preserve,
    )
    executable = Path(arguments.target) / arguments.executable
    subprocess.Popen([str(executable)], cwd=str(executable.parent))


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        error_file = Path(tempfile.gettempdir()) / "automation_update_error.txt"
        error_file.write_text(str(exception), encoding="utf-8")
        raise
