# auto-restic
Simple, automated restic backups through configuration files.

## Usage
A configuration file is automatically generated during the first run, if one isn't present.

An example configuration file looks like this:

```
config = {
    "restic-repo": "path/to/restic/backup/repository",
    "restic-password-file": "configuration/restic-password.txt",
    "backup-file": "configuration/paths-to-backup.txt",
    "exclude-file": "configuration/paths-to-exclude.txt",
    "backup-frequency": 21600,
    "keep-backups": -1,
    "backup-on-start": true,
    "last-backed-up": 1234567890
}
```

- `restic-repo`: The path the restic repository resides in. If one doesn't exist, [initialize one.](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html#)

- `restic-password-file`: The path to the text file containing the passoword to your restic repository.

- `backup-file`: Text file containing the paths that will be backed up, one per line.

- `exclude-file`: Text file containing the paths that will be excluded from the backup, one per line.

- `backup-frequency`: How often you want to run the backup, in seconds.

- `keep-backups`: How long to keep the backups for. See [restic's documentation](https://restic.readthedocs.io/en/stable/060_forget.html#removing-snapshots-according-to-a-policy) for `--keep-within duration`. Set to -1 to never remove backups.

- `backup-on-start`: Set this to true if you want the script to run a backup every time it's started.

- `last-backed-up`: Keeps track of when the last backup was performed, so a backup won't be started if you restart the script immediately after a backup.


## Running
The simplest way to run the script is either through screen on nohup. With nohup, running the program is as simple as `nohup python3 auto-restic.py &`.
