import tomlkit
from tomlkit.toml_document import TOMLDocument

"""
https://toml.io/en/v1.0.0
https://www.toml-lint.com/
https://tomlkit.readthedocs.io/en/latest/api/
"""


class config:
    FILE: str = "config.cfg"

    def __init__(self) -> None:
        self.load()
        return

    def load(self) -> None:
        try:
            with open(self.FILE, mode="rt", encoding="utf-8") as f:
                self.cfg: TOMLDocument = tomlkit.load(f)

        except Exception:
            pass
        return

    def save(self) -> None:
        with open(self.FILE, mode="r+t", encoding="utf-8") as fp:
            fp.write(tomlkit.dumps(self.cfg))
        return

    # get the index of the crawler in the config using the sites url. returns -1 if not found
    def get_crawler_index(self, site: str, crawler: str = "xenforo") -> int:
        self.load()
        if not hasattr(self, "cfg"):
            return -1

        x = self.cfg.get("crawler")
        if not isinstance(x, dict):
            return -1

        x = x[crawler]
        if not isinstance(x, list):
            return -1

        for count, value in enumerate(x):
            if value.get("url") == site:
                return count
        return -1

    # get the index of the section for crawler section. returns -1 if not found
    def get_sub_index(self, cfg, sub: str) -> int:
        for count, value in enumerate(cfg["subs"]):
            if value[0] == sub:
                return count
        return -1
