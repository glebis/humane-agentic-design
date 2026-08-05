"""Serve a built page over http://localhost.

Not a convenience. Opened as a `file://` URL the page loses `navigator.clipboard`
(not a secure context), so "Copy link" silently fails — and that is the feature
that makes a specimen shareable.
"""

import functools
import http.server
import pathlib
import socketserver
import threading
import webbrowser

FIRST_PORT = 8788


def _bind(directory, port):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(directory))
    socketserver.TCPServer.allow_reuse_address = True
    return socketserver.TCPServer(("127.0.0.1", port), handler)


def serve(directory, filename, port=None, open_browser=True):
    """Block serving `directory`. Returns only on Ctrl-C."""
    directory = pathlib.Path(directory).resolve()
    ports = [port] if port else range(FIRST_PORT, FIRST_PORT + 20)
    httpd = None
    for p in ports:
        try:
            httpd = _bind(directory, p)
            break
        except OSError:
            continue
    if httpd is None:
        raise OSError(f"no free port in {ports[0]}..{ports[-1]}"
                      if not port else f"port {port} is in use")

    url = f"http://127.0.0.1:{httpd.server_address[1]}/{filename}"
    print(f"serving {url}  (Ctrl-C to stop)")
    if open_browser:
        threading.Timer(0.3, webbrowser.open, args=(url,)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        httpd.server_close()
    return url
