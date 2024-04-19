import logging
from datetime import datetime, timedelta, timezone
from random import sample
from transmission_rpc import Client
from config import transmission_instances

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
STALE_DAYS = 3
DELETE_DAYS = 7
DOWNLOADING_SECONDS_THRESHOLD = 3600 * 24  # 24 hours in seconds
DEFAULT_ACTIVE_LIMIT = 10

def manage_torrent_status(client, torrent, delete_criteria, stale_criteria):
    """ Manage individual torrent based on its status and criteria. """
    if torrent.is_stalled:
        if torrent.added_date < delete_criteria:
            client.remove_torrent(torrent.id, delete_data=True)
            logging.info(f"Deleted torrent {torrent.name} due to inactivity. Added date: {torrent.added_date}")
        elif torrent.added_date < stale_criteria:
            client.stop_torrent(torrent.id)
            logging.info(f"Stopped stalled torrent: {torrent.name}.  Added date: {torrent.added_date}")
    elif torrent.status == 'downloading' and torrent.percent_done < 0.1 and torrent.seconds_downloading > DOWNLOADING_SECONDS_THRESHOLD:
        client.stop_torrent(torrent.id)
        logging.info(f"Stopped slow downloading torrent: {torrent.name}.  Added date: {torrent.added_date}")

def manage_active_torrents(client, active_limit):
    """ Ensure the number of active torrents does not exceed the limit. """
    torrents = client.get_torrents()
    active_torrents = [t for t in torrents if t.percent_done > 0 and t.status == 'downloading']
    torrents_to_start = [t for t in torrents if t.percent_done == 0]

    if len(active_torrents) < active_limit:
        to_start_count = min(active_limit - len(active_torrents), len(torrents_to_start))
        if to_start_count > 0:
            for torrent in sample(torrents_to_start, to_start_count):
                client.start_torrent(torrent.id)
                logging.info(f"Started torrent: {torrent.name}")

def manage_torrents(client_config):
    """ Connect to the Transmission client and manage torrents based on defined criteria. """
    try:
        client = Client(**client_config)
        logging.info(f"Connected to Transmission on {client_config['host']}")
        delete_criteria = datetime.now(timezone.utc) - timedelta(days=DELETE_DAYS)
        stale_criteria = datetime.now(timezone.utc) - timedelta(days=STALE_DAYS)

        torrents = client.get_torrents()
        for torrent in torrents:
            manage_torrent_status(client, torrent, delete_criteria, stale_criteria)

        manage_active_torrents(client, client_config.get('active_limit', DEFAULT_ACTIVE_LIMIT))

    except Exception as e:
        logging.error(f"Error managing torrents: {e}")

if __name__ == "__main__":
    for instance in transmission_instances:
        logging.info(f"Processing {instance['host']}")
        manage_torrents(instance)
