#!/usr/bin/env python

import argparse
import sys

from os import environ
from pathlib import Path

from src.genesis.genesis import Genesis, GenesisSingleton

repo_root_path = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(repo_root_path))

from src.genesis.cli.args import add_arguments

parser = argparse.ArgumentParser(description="""
    Process genesis from JSON_URL into DB records.
    Environment variables DB_HOST, DB_PORT, DB_USER, DB_PASS, and DB_SCHEMA will override flags.
""")

env_db_host = environ.get("DB_HOST")
env_db_port = environ.get("DB_PORT")
env_db_user = environ.get("DB_USER")
env_db_pass = environ.get("DB_PASS")
env_db_schema = environ.get("DB_SCHEMA")

add_arguments(parser)
args = parser.parse_args()

db_host = env_db_host or args.db_host
if db_host is None:
    raise Exception("either --db-host flag OR DB_HOST env var must be set")

db_port = env_db_port or args.db_port
db_user = env_db_port or args.db_user
db_pass = env_db_port or args.db_pass
db_schema = env_db_port or args.db_schema

# TODO: progress indicator

print("Downloading..")
GenesisSingleton(args.json_url)

# import observers...
# prgramatically import observers moodules...
