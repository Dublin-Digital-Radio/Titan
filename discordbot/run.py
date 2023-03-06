import gc
import argparse

import requests
from config import config

from discordbot.redisqueue import Web


def print_shards():
    token = config["bot-token"]
    url = "https://discordapp.com/api/v6/gateway/bot"
    headers = {"Authorization": "Bot {}".format(token)}
    r = requests.get(url, headers=headers)
    if 200 <= r.status_code < 300:
        print(f"Suggested number of shards: {r.json().get('shards', 0)}")
    else:
        print(f"Status Code: {r.status_code}")
        print(r.text)


def main():
    parser = argparse.ArgumentParser(
        description="Embed Discord like a True Titan (Discord Bot portion)"
    )
    parser.add_argument(
        "-sid", "--shard_id", help="ID of the shard", type=int, default=None
    )
    parser.add_argument(
        "-sc",
        "--shard_count",
        help="Number of total shards",
        type=int,
        default=None,
    )
    parser.add_argument(
        "-s",
        "--shards",
        help="Prints the recommended number of shards to spawn",
        action="store_true",
    )
    args = parser.parse_args()

    if args.shards:
        print_shards()
        return

    print("Starting...")
    te = Web(
        shard_ids=[args.shard_id] if args.shard_id is not None else None,
        shard_count=args.shard_count,
    )
    te.run(config["bot-token"])
    gc.collect()


if __name__ == "__main__":
    main()
