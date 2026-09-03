# README


## Step 1: Backups

1) Locate the module folder
   - On your device open a Explorer window and navigate to `%programdata%\THATec\Modules` (just copy paste it into the URL bar at the top of the window).
   - If this fails, open a prompt asking to provide the thaTEC module directory.`
   - Save the make a variable for that path called `module_folder_path`.
2) In that directory, select the directories `Support` and `thaTEC-Core` and make a `.zip`file from them. Rename the new file `Backup`. Make a copy of `Backup` in the `cwd`.
3) Delete the contents of `thaTEC-Core` (not the entire folder).

## Step 2: Replacing
1) Next to this file, there is a file `thaTEC-core.zip` which contains the new version of `thaTEC-Core`.
2) Unzip the file if needed.
3) Navigate into the folder, select all files and copy them to `%programdata%\THATec\Modules\thaTEC-Core` (or `module_folder_path/thaTEC-Core`)

## Step 3: Startup
1) Open the new `thaTEC-core.exe` with Administrator rights (right click on `thaTEC-core.exe`, look for "Administrator").
2) Here, the user will have to do a few things in the OS. Show a prompt asking if the user has done and if it was succesful.

## Step 4: Reconfigure
1) After Restart:
   Look for the `*backup.zip*\thaTEC-Core\thaTEC-Core.db`-file and replace the one in the new `moudle_folder_path/thaTEC-Core` directory.
   

