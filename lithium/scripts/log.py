from ww.mg.logging import log as mglog

def log(lithium, message: str, parent: mglog | None = None) -> None:
    if lithium.getsetting("verbose"):
        if parent:
            return parent.sublog(message)
        else:
            return mglog(message)