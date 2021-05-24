'''
Automated and scheduled restic backups with configuration files.
'''

import os
import sys
import time
import logging
import datetime

from pathlib import Path

from config import load_config, update_config

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR

BASE_DIR = os.path.dirname(__file__)
SCHEDULER = BackgroundScheduler()
SCHEDULER.start()

def run_backup(config: dict, config_path: str):
	'''
	Run the backup.
	'''
	home = str(Path.home())
	bfile = Path(config["backup-file"])
	efile = Path(config["exclude-file"])
	pfile = Path(config['restic-password-file'])

	# escape spaces in repo path
	repo = Path(config['restic-repo'].replace(" ", "\ "))

	cmd = f'restic -r {repo} backup --files-from {bfile} --verbose --password-file {pfile}'
	if config['exclude-file'] is not None:
		cmd += f' --exclude-file={efile}'

	# run command and clean repository
	os.system(cmd)
	clean_repository(config)

	# update config with update time
	config['last-backed-up'] = int(time.time())
	update_config(config, config_path)

	# schedule next backup
	backup_every_sec = int(config['backup-frequency'])

	backup_dt = datetime.datetime.fromtimestamp(int(time.time()) + backup_every_sec)
	SCHEDULER.add_job(
		run_backup,
		'date', run_date=backup_dt,
		args=[load_config(config_path=CONFIG_DIR), CONFIG_DIR],
		id=f'backup-{int(time.time()) + backup_every_sec}'
	)

	logging.info(f'Backup completed! Next backup scheduled for {backup_dt}')


def clean_repository(config: dict):
	'''
	Prune restic repository after backup.
	'''
	repo = config['restic-repo']
	pfile = os.path.join(BASE_DIR, config['restic-password-file'])
	keep_backups_for = config['keep-backups']

	if keep_backups_for not in ('-1', -1):
		cmd = f'restic -r {repo} forget --keep-within {keep_backups_for} --prune --password-file {pfile}'
	else:
		logging.info('Backups configured to be kept forever: not removing or pruning.')
		return

	os.system(cmd + ' --dry-run')


def apscheduler_event_listener(event):
	'''
	Listens to exceptions coming in from apscheduler's threads.
	'''
	if event.exception:
		logging.critical(f'Error: scheduled job raised an exception: {event.exception}')
		logging.critical('Exception traceback follows:')
		logging.critical(event.traceback)


if __name__ == '__main__':
	CONFIG_DIR = os.path.join(os.path.dirname(__file__), "configuration" , 'restic-config.json')
	SCHEDULER.add_listener(apscheduler_event_listener, EVENT_JOB_ERROR)

	# log path
	log = os.path.join("logs", "backup.log")
	if not os.path.isdir("logs"):
		os.makedirs("logs")

	# init log (disk)
	logging.getLogger('apscheduler').setLevel(logging.WARNING)
	logging.basicConfig(
		filename=log, level=logging.DEBUG,
		format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S'
	)

	conf = load_config(CONFIG_DIR)
	last_backup = conf['last-backed-up']

	if last_backup is None or conf['backup-on-start']:
		logging.info('Backup has never been run: running now...')
		run_backup(conf, CONFIG_DIR)
	else:
		next_backup_unix_ts = int(last_backup) + int(conf['backup-frequency'])
		next_backup_dt = datetime.datetime.fromtimestamp(next_backup_unix_ts)

		if next_backup_unix_ts <= int(time.time()):
			run_backup(conf, CONFIG_DIR)
		else:
			SCHEDULER.add_job(
				run_backup,
				'date', run_date=next_backup_dt,
				args=[load_config(config_path=CONFIG_DIR), CONFIG_DIR], id=f'backup-{next_backup_unix_ts}')

			logging.info(f'Next backup scheduled for {next_backup_dt}')

	while True:
		try:
			time.sleep(3600)
		except KeyboardInterrupt:
			sys.exit('Got ctrl+c: exiting...')
