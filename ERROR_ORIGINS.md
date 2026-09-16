# Origins of `updater.py` Errors

This document explains where errors in `updater.py` originate and what they usually indicate.

## Error-handling flow

`main()` parses the command-line arguments and calls either `run_update()` or `run_restore()`. Several expected operational errors are caught at the end of `main()`:

```python
except (FileNotFoundError, OSError, PermissionError, RuntimeError) as error:
    print(f"Update failed: {error}", file=sys.stderr)
    return 1
```

The error message is printed to standard error and the program exits with status code `1`. Unexpected exception types are not caught and will produce a Python traceback.

`PermissionError` is already a subclass of `OSError`, so listing both does not change the behavior.

## Module-directory errors

### Missing default directory

`get_module_dir()` first checks `%PROGRAMDATA%\\THATec\\Modules`. If the directory is missing and no `--module-dir` argument was provided, `prompt_for_module_dir()` asks the user for another location.

A `FileNotFoundError` occurs when the selected directory does not exist or is not a directory. This can result from an incorrect path, a missing installation, or a typo in the command-line argument.

### Missing required subdirectories

The updater requires both of these directories:

- `Support`
- `thaTEC-Core`

If either directory is missing, `get_module_dir()` raises `FileNotFoundError`. This normally means that the selected directory is not the correct THATec module directory or that the installation is incomplete.

### Path and access errors

`Path.resolve()` may fail if the path cannot be resolved. Later directory operations can raise `OSError` or `PermissionError` when the user does not have sufficient access to the module directory.

## Backup errors

`create_backup()` creates a timestamped ZIP file in the directory containing `updater.py`. It recursively scans `Support` and `thaTEC-Core` and adds every file it finds.

Possible error origins include:

- The updater directory is read-only, preventing creation of the backup ZIP.
- A source file is locked, inaccessible, or deleted while the backup is being created.
- A file path is too long for the operating system or ZIP implementation.
- The disk is full.
- Another backup already has the same timestamped filename.

Only files are added to the archive. Empty directories are not preserved because the code does not explicitly add directory entries.

## Update archive errors

`extract_update()` expects `thaTEC-core.zip` to be next to `updater.py`.

If the archive does not exist, the function raises `FileNotFoundError`. If it is not a valid ZIP file, `ZipFile` raises `BadZipFile`, which is not explicitly caught by `main()` and therefore produces a traceback.

The function extracts the archive into a temporary directory. It looks first for an extracted folder named `thaTEC-core`. If that folder is absent, it treats the temporary directory itself as the source. An incorrectly structured archive can therefore cause the updater to copy the wrong files or fail to find expected files.

The target `thaTEC-Core` directory is cleared before the new files are copied. Deletion can fail with `PermissionError` if files are in use or the process lacks administrator rights. It can also fail with `OSError` for read-only files, invalid paths, or filesystem problems.

The archive is extracted with `extractall()`. The ZIP must be trusted; archives from untrusted sources should be checked for unsafe paths before extraction.

## Missing executable errors

After copying the update, `run_update()` checks for:

```text
thaTEC-Core\\thaTEC-core.exe
```

If this file is missing, `FileNotFoundError` is raised. Common causes are:

- The update ZIP has the wrong internal folder structure.
- The executable has a different name or capitalization.
- The archive was incomplete.
- Files were copied to an unexpected target location.

## Administrator-launch errors

`launch_as_administrator()` behaves differently depending on the operating system.

On non-Windows systems it starts the executable with `subprocess.Popen()`. This can raise `OSError` if the executable cannot be started.

On Windows it calls `ShellExecuteW()` with the `runas` verb. Windows may display a User Account Control prompt. If the user cancels the prompt, or Windows cannot start the program, the returned result may be `32` or less, causing the function to raise `OSError`.

Starting the program successfully only means that Windows accepted the launch request. It does not prove that `thaTEC-core.exe` completed setup successfully. The updater prints `Success.` immediately after launching it and does not wait for the process to exit.

## Database-restore errors

`restore_database()` opens the backup ZIP and searches its names for an entry ending with:

```text
thaTEC-Core/thaTEC-Core.db
```

Backslash separators are converted to forward slashes first so that Windows-style ZIP entries can also be recognized.

A `FileNotFoundError` occurs if no matching database entry is found. This may indicate that:

- The backup was created from the wrong directory.
- The database did not exist when the backup was made.
- The selected backup is not a backup produced by this updater.
- The ZIP uses an unexpected internal path.

The restore can also fail if the backup is missing, corrupt, inaccessible, or currently locked. Opening the destination database for writing can raise `PermissionError` if the file is in use or the user lacks write access.

The database is copied with `shutil.copyfileobj()`, which streams the data from the ZIP into the destination file. If the operation is interrupted, the destination file may be incomplete.

## Restore-mode errors

With `--restore`, the updater skips the installation process and restores the database from an existing backup.

If `--backup` is omitted, the updater searches next to `updater.py` for files matching:

```text
Backup-*.zip
```

It lists the matching files from newest to oldest and prompts for the number of the backup to restore. If no matching file exists, it raises `FileNotFoundError`. Use `--backup` to select a backup by path instead, including one stored elsewhere.

## Command-line errors

`argparse` handles invalid command-line syntax before the update starts. For example, an unknown option or a missing value for `--module-dir` causes `argparse` to display an error and exit.

The `--restore` option controls the mode. The `--backup` argument is used only by restore mode; it does not select the backup filename used during a normal update.

## Practical troubleshooting order

When an error occurs, check the following in order:

1. Confirm that the selected module directory contains `Support` and `thaTEC-Core`.
2. Confirm that `thaTEC-core.zip` is beside `updater.py`.
3. Inspect the ZIP structure and verify that it contains the new core files.
4. Run the updater with appropriate permissions.
5. Close thaTEC-Core and related processes before replacing files.
6. Check that the backup ZIP was created and contains `thaTEC-Core/thaTEC-Core.db`.
7. If the final restore is interrupted, run `python updater.py --restore --backup <backup-file>`.
8. Check the exit code: `0` indicates success, while `1` indicates one of the handled update or restore errors.
