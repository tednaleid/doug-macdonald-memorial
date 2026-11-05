#!/usr/bin/env python3
# ABOUTME: Static file server with HTTP Range support so the page can seek in the audio file.
# ABOUTME: Run via `python3 serve.py [port] [directory]`; stdlib only. Copied from diarization-prototype.
"""Range-capable static server for the diarization player.

Python's stock http.server ignores Range requests and returns the whole file,
which makes <audio> seeking stall on a 2-hour MP3. This adds 206 Partial Content
so skipping around is responsive.
"""
import http.server
import os
import re
import sys

CHUNK = 64 * 1024


class RangeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        range_header = self.headers.get("Range")
        path = self.translate_path(self.path)
        if range_header and os.path.isfile(path):
            self.serve_range(path, range_header)
        else:
            super().do_GET()

    def serve_range(self, path, range_header):
        size = os.path.getsize(path)
        m = re.match(r"bytes=(\d*)-(\d*)\s*$", range_header)
        if not m or (m.group(1) == "" and m.group(2) == ""):
            self.send_error(400, "Bad Range")
            return
        if m.group(1) == "":  # suffix: bytes=-N
            length = int(m.group(2))
            start = max(0, size - length)
            end = size - 1
        else:
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else size - 1
        end = min(end, size - 1)
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return

        length = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(length))
        self.end_headers()

        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(CHUNK, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    break
                remaining -= len(chunk)


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    os.chdir(sys.argv[2] if len(sys.argv) > 2 else ".")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), RangeHandler)
    print(f"serving {os.getcwd()} on http://127.0.0.1:{port} (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
