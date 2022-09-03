import logging
import os
import sys

import ujson as json

BASE_DIR = os.path.dirname(__file__)


def create_config():
	"""
	Create a new configuration and associated files.
	"""

	# repository path
	repo_path = input("restic repository path: ")

	# ask for password file path and password
	pw_path = input(
		"restic password file path (configuration/restic-password.txt): ")
	if pw_path == "":
		pw_path = os.path.join(BASE_DIR, "configuration",
			"restic-password.txt")

	with open(pw_path, "w") as pw_file:
		pw_file.write(input("Enter restic repository password: "))

	# backup frequency
	backup_freq = int(eval(input("Backup every .. seconds (e.g. 3600*24): ")))
	if backup_freq == "":
		backup_freq = 3600 * 24

	# keep backups
	keep_backups = input("Time to keep backups (e.g. 2y5m7d3h, -1=forever): ")
	if keep_backups == "":
		keep_backups = "-1"

	paths_to_backup = []
	inp = input("\nAdd paths/files to BACKUP (enter when done): ")
	while inp != "":
		paths_to_backup.append(inp)
		inp = input("Add paths/files to BACKUP (enter when done): ")

	paths_to_exclude = []
	inp = input("\nAdd paths/files to EXCLUDE (enter when done): ")
	while inp != "":
		paths_to_exclude.append(inp)
		inp = input("Add paths/files to EXCLUDE (enter when done): ")

	# write paths to file
	backup_paths_fname = os.path.join(BASE_DIR, "configuration",
		"paths-to-backup.txt")
	with open(backup_paths_fname, "w") as backup_file:
		backup_file.write("\n".join(paths_to_backup))

	# create exclude file
	exclude_paths_fname = os.path.join(BASE_DIR, "configuration",
		"paths-to-exclude.txt")
	with open(exclude_paths_fname, "w") as exclude_file:
		exclude_file.write("\n".join(paths_to_exclude))

	# backup on startup?
	inp = input("\nAlways backup on script startup? (y/N): ")
	backup_on_start = bool(inp.lower() in ("y", "yes"))

	# creat config
	config = {
		"restic-repo": repo_path,
		"restic-password-file": pw_path,
		"backup-file": backup_paths_fname,
		"exclude-file": exclude_paths_fname,
		"backup-frequency": backup_freq,
		"keep-backups": keep_backups,
		"backup-on-start": backup_on_start,
		"last-backed-up": None
	}

	return config


def update_config(new_config: dict, config_path):
	"""
	Dump updated config to disk.
	"""
	# tmp file path
	tmp_file_path = config_path.parent / "tmp.json"

	# open tmp file
	try:
		with open(tmp_file_path, "w") as tmp_file:
			json.dump(new_config, tmp_file, indent=4)
	except:
		logging.exception("⚠️ Error dumping updated config!")
		os.remove(tmp_file_path)
		return

	# if successful, rename temp file
	os.rename(tmp_file_path, config_path)


def load_config(config_path: str):
	"""
	Load config from path.
	"""
	if not os.path.isfile(config_path):
		with open(config_path, "w") as config_file:
			try:
				json.dump(create_config(), config_file, indent=4)
			except:
				logging.exception(
					"Loading config failed in load_config (file did not exist)"
				)

	try:
		with open(config_path, "r") as config_file:
			return json.load(config_file)
	except ValueError:
		sys.exit("Error loading configuration file!")
