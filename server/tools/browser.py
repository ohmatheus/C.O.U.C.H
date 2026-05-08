import subprocess
import urllib.parse
from typing import Any


def search_youtube(query: str, state: dict[str, Any]) -> str:
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    subprocess.Popen(["xdg-open", url])
    state["active_app"] = "youtube"
    state["last_search"] = query
    return f"Recherche YouTube lancée : {query}"
