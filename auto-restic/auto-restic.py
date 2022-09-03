"""
Automated and scheduled restic backups with configuration files.
"""

import os
import sys
import time
import logging
import datetime
import argparse

from pathlib import Path

from config import load_config, update_config

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR

BASE_DIR = Path(os.path.dirname(__file__))
CONFIG_DIR = BASE_DIR / "configuration" / "restic-config.json"
CONFIG = load_config(CONFIG_DIR)

SCHEDULER = BackgroundScheduler()
SCHEDULER.start()


def run_backup():
	"""
	Run the backup.
	"""
	backup_file = BASE_DIR / CONFIG["backup-file"]
	exclude_file = BASE_DIR / CONFIG["exclude-file"]
	password_file = BASE_DIR / CONFIG["restic-password-file"]

	# Escape spaces in repo path
	repo = Path(CONFIG["restic-repo"].replace(" ", "\ "))

	# Build the command
	cmd = f"restic -r {repo} backup --files-from {backup_file} --verbose --password-file {password_file}"
	if CONFIG["exclude-file"] is not None:
		cmd += f" --exclude-file={exclude_file}"

	# Run command and clean repository
	os.system(cmd)
	clean_repository()

	# Update config with update time
	CONFIG["last-backed-up"] = int(time.time())

	# Datetime of next backup
	backup_dt = datetime.datetime.fromtimestamp(
		int(time.time()) + int(CONFIG["backup-frequency"]))

	SCHEDULER.add_job(run_backup, "date", run_date=backup_dt)
	logging.info(f"Backup completed! Next backup scheduled for {backup_dt}")


def clean_repository():
	"""
	Prune restic repository after backup.
	"""
	repo = CONFIG["restic-repo"]
	password_file = BASE_DIR / CONFIG["restic-password-file"]
	keep_backups_for = CONFIG["keep-backups"]

	if keep_backups_for not in ("-1", -1):
		cmd = f"restic -r {repo} forget --keep-within {keep_backups_for} --prune --password-file {password_file}"
	else:
		logging.info(
			"Backups configured to be kept forever: not removing or pruning.")
		return

	os.system(cmd + " --dry-run")


def apscheduler_event_listener(event):
	"""
	Listens to exceptions coming in from apscheduler"s threads.
	"""
	if event.exception:
		logging.critical(
			f"Error: scheduled job raised an exception: {event.exception}")
		logging.critical("Exception traceback follows:")
		logging.critical(event.traceback)


if __name__ == "__main__":
	# Setup argparse
	parser = argparse.ArgumentParser("auto-restic.py")
	parser.add_argument("--run-once",
		dest="run_once",
		action="store_true",
		help="Specify to only run the program once")

	# Set defaults, parse
	parser.set_defaults(run_once=False)
	args = parser.parse_args()

	# Listen for exceptions raised by events
	SCHEDULER.add_listener(apscheduler_event_listener, EVENT_JOB_ERROR)

	# Log path
	log = BASE_DIR / "logs" / "backup.log"
	if not Path(BASE_DIR / "logs").is_dir():
		Path(BASE_DIR / "logs").mkdir()

	# Init log (disk)
	logging.getLogger("apscheduler").setLevel(logging.WARNING)
	logging.basicConfig(filename=str(log),
		level=logging.DEBUG,
		format="%(asctime)s %(message)s",
		datefmt="%d/%m/%Y %H:%M:%S")

	last_backup = CONFIG["last-backed-up"]

	if last_backup is None or CONFIG["backup-on-start"]:
		if CONFIG["backup-on-start"]:
			logging.info(
				"Backup configured to run on program start: running now...")
		else:
			logging.info("Backup has never been run: running now...")

		run_backup()
	else:
		next_backup_unix_ts = int(last_backup) + int(
			CONFIG["backup-frequency"])
		next_backup_dt = datetime.datetime.fromtimestamp(next_backup_unix_ts)

		if next_backup_unix_ts <= int(time.time()):
			run_backup()
		else:
			SCHEDULER.add_job(run_backup, "date", run_date=next_backup_dt)
			logging.info(f"Next backup scheduled for {next_backup_dt}")

	if not args.run_once:
		while True:
			try:
				time.sleep(3600)
			except KeyboardInterrupt:
				update_config(CONFIG, CONFIG_DIR)
				sys.exit("Got ctrl+c: exiting...")

	# Save config on shutdown
	update_config(CONFIG, CONFIG_DIR)
