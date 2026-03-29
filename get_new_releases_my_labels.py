"""CLI: retrieve new releases from your followed Beatport labels including artwork."""

import argparse
import asyncio
import os

from dotenv import load_dotenv

from beatport_client import BeatportClient

load_dotenv()


async def main(num_releases: int):
    client = BeatportClient(
        username=os.environ["BEATPORT_USERNAME"],
        password=os.environ["BEATPORT_PASSWORD"],
        base_url=os.environ["BEATPORT_BASE_URL"],
        access_token=os.environ.get("BEATPORT_ACCESS_TOKEN"),
        refresh_token=os.environ.get("BEATPORT_REFRESH_TOKEN"),
        token_expires_at=float(os.environ.get("BEATPORT_TOKEN_EXPIRES_AT", 0)),
    )

    try:
        followed_labels = await client._api_get("/my/beatport/labels/", per_page=100)
        if not followed_labels:
            print("You are not following any labels.")
            return

        print(f"Following {len(followed_labels)} label(s) — showing up to {num_releases} releases each\n")

        for label_info in followed_labels:
            label_id = label_info["id"]
            label_name = label_info["name"]
            label_artwork = (
                label_info.get("image", {})
                .get("dynamic_uri", "")
                .replace("{w}x{h}", "500x500")
            )

            print(f"{'=' * 60}")
            print(f"  {label_name} (id={label_id})")
            print(f"  Artwork: {label_artwork}")
            print(f"{'=' * 60}\n")

            releases = await client._api_get(
                "/catalog/releases/",
                label_id=label_id,
                per_page=num_releases,
                ordering="-publish_date",
            )
            items = releases if isinstance(releases, list) else releases.get("results", [])

            if not items:
                print("  No releases found.\n")
                continue

            for release in items:
                artists = ", ".join(a["name"] for a in release.get("artists", []))
                artwork_url = (
                    release.get("image", {})
                    .get("dynamic_uri", "")
                    .replace("{w}x{h}", "500x500")
                )

                print(f"  {release.get('publish_date', 'n/a')}  {release['name']}")
                print(f"  Artists: {artists}")
                print(f"  Catalog#: {release.get('catalog_number', 'n/a')}")
                print(f"  Artwork:  {artwork_url}")
                print()

    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Get new releases from your followed Beatport labels."
    )
    parser.add_argument(
        "-n", "--num-releases",
        type=int,
        default=10,
        help="number of releases to show per label (default: 10)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.num_releases))
