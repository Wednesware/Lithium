from lithium.ww.mg26_11.logging import log as mglog

def log(perkeo, message: str, parent: mglog | None = None) -> mglog:
    if perkeo.getsetting("verbose"):
        if parent:
            return parent.sublog(message)
        else:
            return mglog(message)