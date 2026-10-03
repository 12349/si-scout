import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ui.app import create_app

flask_app = create_app({"DEMO": True})

def app(environ, start_response):
    path_info = environ.get("PATH_INFO", "")
    qs = environ.get("QUERY_STRING", "")

    # Check if __orig_path was passed via rewrite
    if "__orig_path=" in qs:
        params = parse_qs(qs, keep_blank_values=True)
        if "__orig_path" in params:
            orig = params.pop("__orig_path")[0]
            # Reconstruct query string without __orig_path
            new_qs_pairs = []
            for k, vals in params.items():
                for v in vals:
                    new_qs_pairs.append((k, v))
            environ["QUERY_STRING"] = urlencode(new_qs_pairs)
            environ["PATH_INFO"] = orig if orig.startswith("/") else f"/{orig}"
    elif path_info in ("/api/index.py", "/api/index"):
        environ["PATH_INFO"] = "/"

    return flask_app(environ, start_response)
