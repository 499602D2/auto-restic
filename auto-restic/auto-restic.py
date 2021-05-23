'''
Automated and scheduled restic backups with configuration files.
'''

import os
import sys
import time
import logging
import datetime

from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR

import ujson as json

BASE_DIR = os.path.dirname(__file__)
SCHEDULER = BackgroundScheduler()
SCHEDULER.start()

def run_backup(config: dict, config_path: str):
	'''
	Run the backup.
	'''
	home = str(Path.home())
	repo = config['restic-repo']
	pfile = os.path.join(BASE_DIR, config['restic-password-file'])

	backup_paths = []
	for path in config['backup-paths']:
		#backup_paths.append(os.path.join(home, path))
		backup_paths.append(path)

	backup_paths = ' '.join(backup_paths)

	cmd = f'restic -r {repo} backup {backup_paths} --verbose --password-file {pfile}'
	if config['exclude-file'] is not None:
		cmd += f' --exclude-file={config["exclude-file"]}'

	# run command and clean repository
	os.system(cmd)
	clean_repository(config)

	# update config with update time
	config['last-backed-up'] = int(time.time())
	update_config(config, config_path)

	# schedule next backup
	backup_every_sec = int(config['backup-frequency'])

	next_backup_unix_ts = int(time.time()) + backup_every_sec
	next_backup_dt = datetime.datetime.fromtimestamp(next_backup_unix_ts)
	SCHEDULER.add_job(
		run_backup,
		'date', run_date=next_backup_dt,
		args=[load_config(config_path=CONFIG_DIR), CONFIG_DIR], id=f'backup-{next_backup_unix_ts}')

	logging.info(f'Backup completed! Next backup scheduled for {next_backup_dt}')


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


def update_config(new_config: dict, config_path: str):
	'''
	Dump updated config to disk.
	'''
	with open(config_path, 'w') as config_file:
		json.dump(new_config, config_file, indent=4)


def load_config(config_path: str):
	'''
	Load config from path.
	'''
	if not os.path.isfile(config_path):
		with open(config_path, 'w') as config_file:
			json.dump(create_config(), config_file, indent=4)

	with open(config_path, 'r') as config_file:
		return json.load(config_file)


def create_config():
	'''
	Config keys
		restic-repo: repository, e.g. fspath or rclone path
		backup-frequency: how often to backup in seconds
		keep-backup: keep backups for y/m/d/h (e.g. 2y5m7d3h, -1 == forever)
		exclude-file: exclusion file
		backup-paths: list of paths to backup, relative to home folder
	'''

	'''
	TODO convert to a setup function
	-- A sample config --
	config = {
		'restic-repo': 'rclone:Dropbox:Restic',
		'restic-password-file': 'restic-password.txt',
		'backup-frequency': 3600*12,
		'keep-backups': '1y0m0d0h',
		'exclude-file': 'excludes.txt',
		'last-backed-up': None,

		'backup-paths': [
		]
	}
	'''

	config = {
		'restic-repo': input('restic repository path: '),
		'restic-password-file': input('restic password file (restic-password.txt): '),
		'backup-frequency': input('Backup every .. seconds (3600*12): '),
		'keep-backups': -1,
		'exclude-file': input('Exlusion file (excludes.txt): '),
		'last-backed-up': None,

		'backup-paths': []
	}

	inp = input('Add paths/files to backup (enter when done): ')
	while inp != '':
		if ' ' in inp:
			inp_spl = inp.split('/')
			for enum, split in enumerate(inp_spl):
				if ' ' in split:
					inp_spl[enum] = f"'{split}'"

			inp = '/'.join(inp_spl)

		config['backup-paths'].append(inp)
		inp = input('Add paths/files to backup (enter when done): ')

	return config


def apscheduler_event_listener(event):
	'''
	Listens to exceptions coming in from apscheduler's threads.
	'''
	if event.exception:
		logging.critical(f'Error: scheduled job raised an exception: {event.exception}')
		logging.critical('Exception traceback follows:')
		logging.critical(event.traceback)


if __name__ == '__main__':
	CONFIG_DIR = os.path.join(os.path.dirname(__file__), 'restic-config.json')
	SCHEDULER.add_listener(apscheduler_event_listener, EVENT_JOB_ERROR)

	# init log (disk)
	log = os.path.join('backup.log')
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
