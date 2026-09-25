"""Update thaTEC-Core while keeping a restorable backup of the current files."""

from __future__ import annotations

import argparse
import ctypes
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from zipfile import ZIP_DEFLATED, ZipFile
import sqlite3


ARCHIVE_NAME = "thaTEC-core.zip"
BACKUP_PREFIX = "Backup-"

logger = logging.getLogger("updater")


def setup_logging() -> Path:
    """Log to the console and to a log file next to the script or the built executable."""
    if getattr(sys, "frozen", False):
        log_path = Path(sys.executable).resolve().with_suffix(".log")
    else:
        log_path = Path(__file__).resolve().with_suffix(".log")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(process)d] %(levelname)s %(message)s"))

    logger.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    sys.excepthook = log_uncaught_exception
    return log_path


def log_uncaught_exception(exc_type, exc_value, exc_traceback) -> None:
    logger.critical("Unhandled error", exc_info=(exc_type, exc_value, exc_traceback))


def ask(prompt: str) -> str:
    """input() that also records the prompt and the answer in the log file."""
    answer = input(prompt)
    logger.debug("Prompt %r answered with %r", prompt, answer)
    return answer


def prompt_for_module_dir() -> Path:
    default = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "THATec" / "Modules"
    answer = ask(f"Module directory (default: {default}): ").strip().strip('"')
    return Path(answer) if answer else default


def get_module_dir(argument: str | None) -> Path:
    default = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "THATec" / "Modules"
    module_dir = Path(argument).expanduser() if argument else default
    if not argument and not module_dir.is_dir():
        module_dir = prompt_for_module_dir()
    module_dir = module_dir.resolve()
    if not module_dir.is_dir():
        raise FileNotFoundError(f"Module directory does not exist: {module_dir}")
    for name in ("Support", "thaTEC-Core"):
        if not (module_dir / name).is_dir():
            raise FileNotFoundError(f"Missing required directory: {module_dir / name}")
    return module_dir


def create_backup(module_dir: Path, workspace: Path) -> Path:
    backup_path = workspace / f"{BACKUP_PREFIX}{datetime.now():%Y%m%d-%H%M%S}.zip"
    with ZipFile(backup_path, "w", ZIP_DEFLATED) as archive:
        for directory_name in ("Support", "thaTEC-Core"):
            directory = module_dir / directory_name
            for path in directory.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(module_dir))
    return backup_path


def clear_directory(directory: Path) -> None:
    for child in directory.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def extract_update(archive_path: Path, target: Path) -> None:
    if not archive_path.is_file():
        raise FileNotFoundError(f"Update archive not found: {archive_path}")

    with tempfile.TemporaryDirectory(prefix="thatec-update-") as temporary_dir:
        extraction_dir = Path(temporary_dir)
        with ZipFile(archive_path) as archive:
            archive.extractall(extraction_dir)

        source = extraction_dir / "thaTEC-core"
        if not source.is_dir():
            source = extraction_dir
        clear_directory(target)
        for item in source.iterdir():
            destination = target / item.name
            shutil.copytree(item, destination) if item.is_dir() else shutil.copy2(item, destination)


def restore_database(backup_path: Path | None, module_dir: Path) -> Path:
    if backup_path is None:
        backup_path = select_backup(Path(__file__).resolve().parent)
    if backup_path is None:
        logger.info('No backup was selected.')
        return
    database_target = module_dir / "thaTEC-Core" / "thaTEC-Core.db"
    with ZipFile(backup_path) as archive:
        database_name = next(
            (name for name in archive.namelist() if name.replace("\\", "/").endswith("thaTEC-Core/thaTEC-Core.db")),
            None,
        )
        if database_name is None:
            raise FileNotFoundError(f"No thaTEC-Core.db found in {backup_path}")
        with archive.open(database_name) as source, database_target.open("wb") as destination:
            shutil.copyfileobj(source, destination)
    return backup_path


def launch_as_administrator(executable: Path) -> None:
    if os.name != "nt":
        subprocess.Popen([str(executable)], cwd=executable.parent)
        return
    result = ctypes.windll.shell32.ShellExecuteW(None,
                                                 "runas",
                                                 str(executable),
                                                 None, str(executable.parent),
                                                 1)
    if result <= 32:
        raise OSError(f"Could not start {executable} with administrator rights (error {result}).")


def relaunch_as_administrator() -> bool:
    """Restart this program elevated. Returns True if an elevated instance was started."""
    if os.name != "nt" or ctypes.windll.shell32.IsUserAnAdmin():
        return False
    if getattr(sys, "frozen", False):
        parameters = subprocess.list2cmdline(sys.argv[1:])
    else:
        parameters = subprocess.list2cmdline([str(Path(__file__).resolve()), *sys.argv[1:]])
    # ShellExecuteW blocks until the user has answered the UAC prompt.
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, parameters, os.getcwd(), 1)
    if result <= 32:
        raise PermissionError(f"Could not obtain administrator rights (error {result}).")
    return True


def select_backup(workspace: Path) -> Path | None:
    backups = sorted(workspace.glob(f"{BACKUP_PREFIX}*.zip"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not backups:
        raise FileNotFoundError(f"No {BACKUP_PREFIX}*.zip backup found in {workspace}")

    logger.info("Available backups:")
    logger.info("0. None")
    for number, backup in enumerate(backups, start=1):
        logger.info(f"{number}. {backup.name}")

    while True:
        answer = ask("Enter the number of the backup to restore: ").strip()
        try:
            selection = int(answer)
        except ValueError:
            logger.info("Please enter a valid backup number.")
            continue
        if 1 <= selection <= len(backups):
            return backups[selection - 1]
        elif selection == 0:
           return None 
        logger.info(f"Please enter a number between 1 and {len(backups)}.")


def run_update(module_argument: str | None) -> None:
    workspace = Path(__file__).resolve().parent
    module_dir = get_module_dir(module_argument)
    backup_path = create_backup(module_dir, workspace)
    wait_enter_print(f"Created backup: {backup_path}.\nPress Enter to continue...", 'Continuing...')
    backup_path = None

    extract_update(workspace / ARCHIVE_NAME, module_dir / "thaTEC-Core")
    executable = module_dir / "thaTEC-Core" / "thaTEC-core.exe"
    if not executable.is_file():
        raise FileNotFoundError(f"Updated executable was not found: {executable}")
    logger.info(f"Installed update in {module_dir / 'thaTEC-Core'}")
    wait_enter_print("The updater will now attempt to start thaTEC-Core as administrator. In case of an error, simply start it yourself." \
	"\nPress Enter to continue...", 'Continuing')
    launch_as_administrator(executable)
    logger.info('Success.')
    # wait_enter_print("Complete the thaTEC-Core setup and restart if requested. Press Enter to continue...", 'Continuing')
    # restore_database(backup_path, module_dir)
    # print(f"Restored database from {backup_path}")


def run_restore(module_argument: str | None, backup_argument: str | None) -> None:
    module_dir = get_module_dir(module_argument)
    backup_path = Path(backup_argument).expanduser().resolve() if backup_argument else None
    restored_from = restore_database(backup_path, module_dir)
    logger.info(f"Restored database from {restored_from}")

def wait_enter_print(before, after):
    ask(before)
    logger.info(after)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module-dir", help="Path to THATec\\Modules")
    parser.add_argument("--restore", action="store_true", help="Only restore the database from an existing backup")
    parser.add_argument("--backup", help="Backup zip to use with --restore")
    log_path = setup_logging()
    arguments = parser.parse_args()
    logger.debug("Started with arguments %r, logging to %s", sys.argv, log_path)

    if relaunch_as_administrator():
        logger.debug("Restarted with administrator rights, exiting this instance.")
        return 0

    try:
        if arguments.restore:
            run_restore(arguments.module_dir, arguments.backup)
        else:
            run_update(arguments.module_dir)
    except (FileNotFoundError, OSError, PermissionError, RuntimeError) as error:
        logger.error(f"Update failed: {error}")
        logger.debug("Traceback:", exc_info=True)
        return 1
    ask('Press Enter to close the program...')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
