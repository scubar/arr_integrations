from transmission_rpc import Client
from datetime import datetime, timedelta, timezone
import random
from config import transmission_instances

# Define the stale criteria (e.g., no progress in the last 1 day)
stale_criteria = datetime.now(timezone.utc) - timedelta(days=1)

def manage_torrents(client_config):
    # Connect to Transmission
    client = Client(host=client_config['host'], port=client_config['port'], 
                    username=client_config['username'], password=client_config['password'])

    # Fetch all torrents
    torrents = client.get_torrents()

    # Process stale or slow torrents first
    for torrent in torrents:
        if torrent.is_stalled and torrent.added_date < stale_criteria:
            client.stop_torrent(torrent.id)
            print(f"Stopped Stale Torrent on {client_config['host']}: {torrent.name} (ID: {torrent.id}, Added on: {torrent.added_date.strftime('%Y-%m-%d')})")
        elif torrent.status == 'downloading' and torrent.percent_done < 0.1 and torrent.seconds_downloading > 7200:
            client.stop_torrent(torrent.id)
            print(f"Stopped Slow Torrent on {client_config['host']}: {torrent.name} (ID: {torrent.id}, Downloading for: {torrent.seconds_downloading} seconds)")
        elif torrent.status == 'stopped':
            # List the name of the stopped torrents
             print(f"Skipping Stopped Torrent on {client_config['host']}: {torrent.name} (ID: {torrent.id})")

    # Determine the limit for active torrents for this instance
    active_limit = client_config.get('active_limit', 10)  # Use specified limit or default to 10

    # Grab torrents again
    torrents = client.get_torrents()

    # Filter torrents based on specific criteria after processing for stale or slow torrents
    active_torrents = [torrent for torrent in torrents if torrent.percent_done > 0 and (torrent.status == 'downloading')]
    torrents_to_start = [torrent for torrent in torrents if torrent.percent_done == 0]

    # If the active torrents are fewer than the active_limit, start torrents randomly that have not downloaded any data yet
    if len(active_torrents) < active_limit:
        needed_torrents = active_limit - len(active_torrents)
        if needed_torrents > len(torrents_to_start):
            needed_torrents = len(torrents_to_start)
        torrents_to_start_randomly = random.sample(torrents_to_start, needed_torrents)

        for torrent in torrents_to_start_randomly:
            client.start_torrent(torrent.id, True)
            print(f"Started Torrent on {client_config['host']}: {torrent.name} (ID: {torrent.id})")

if __name__ == "__main__":
    for instance in transmission_instances:
        print(f"Processing {instance['host']}")
        manage_torrents(instance)
