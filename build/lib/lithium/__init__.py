from .ww.he26_16 import Project


VERSION: str = "26.1"

def main():
    perkeo: Project = Project(__file__, ".")
    perkeo.version = VERSION
    perkeo.script.runpk()