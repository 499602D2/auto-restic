# auto-restic
Simple, automated restic backups through configuration files.

## Usage
A configuration file is automatically generated during the first run, if one isn't present.

An example configuration file looks like this:

```
config = {
    'restic-repo': 'rclone:Dropbox:Restic',
    'restic-password-file': 'restic-password.txt',
    'backup-frequency': 3600*12,
    'keep-backups': '1y0m0d0h',
    'exclude-file': 'excludes.txt',
    'last-backed-up': None,

    'backup-paths': [
        "foo/bar",
        "important/files"
    ]
}
```

- `restic-repo`: The path the restic repository resides in. If one doesn't exist, [initialize one.](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html#)

- `restic-password-file`: The path to the text file containing the passoword to your restic repository.

- `backup-frequency`: How often you want to run the backup, in seconds. You can use expressions like in the example.

- `keep-backups`: How long to keep the backups for. See [restic's documentation](https://restic.readthedocs.io/en/stable/060_forget.html#removing-snapshots-according-to-a-policy) for `--keep-within duration`.

- `exclude-file`: Text file containing the files that will be excluded from the backup, one per line.

- `last-backed-up`: Keeps track of when the last backup was performed, so a backup won't be started if you restart the script immediately after a backup.

- `backup-paths`: List of paths that will be backed up. Could, and probably should, be a text file.


## Running
The simplest way to run the script is either through screen on nohup. With nohup, running the program is as simple as `nohup python3 auto-restic.py &`.
