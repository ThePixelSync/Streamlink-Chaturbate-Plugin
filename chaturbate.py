"""
$description Global live-streaming platform.
$url chaturbate.com
$type live
$metadata author
$metadata title
$metadata category
"""

import logging
import re
import uuid

from streamlink.plugin import Plugin, pluginmatcher, PluginError
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)

API_HLS = "https://chaturbate.com/get_edge_hls_url_ajax/"

@pluginmatcher(
    re.compile(r"https?://(?:www\.)?chaturbate\.com/(?P<username>[^/]+)/?"),
)

class Chaturbate(Plugin):
    def _get_streams(self):
        username = self.match.group("username")
        log.info(f"Fetching stream for user: {username}")

        CSRFToken = uuid.uuid4().hex.upper()[0:32]

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRFToken": CSRFToken,
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self.url,
        }

        cookies = {
            "csrftoken": CSRFToken,
        }

        post_data = f"room_slug={username}&bandwidth=high"

        try:
            log.debug(f"Sending POST request to {API_HLS}")
            log.debug(f"Data: {post_data}")

            res = self.session.http.post(
                API_HLS,
                headers=headers,
                cookies=cookies,
                data=post_data,
                schema=validate.Schema(
                    validate.parse_json(),
                    {
                        "url": validate.any(None, str),
                        "room_status": str,
                        "success": validate.any(bool, int),
                    },
                    validate.union_get(
                        "url",
                        "room_status",
                        "success"
                    )
                ),
            )
            hls_url, room_status, success = res

            log.debug(f"API response: url={hls_url}, status={room_status}, success={success}")

        except PluginError as err:
            log.error(f"Failed to connect to API: {err}")
            return
        except validate.SchemaError as err:
            log.error(f"Failed to validate API response: {err}")
            return

        log.info(f"Stream status: {room_status}, success={success}")

        if success and room_status == "public" and hls_url:
            log.info("Found a live stream. Attempting to parse HLS playlist.")
            return HLSStream.parse_variant_playlist(self.session, hls_url)
        else:
            log.info("No playable stream found. Channel may be offline or private.")


__plugin__ = Chaturbate
