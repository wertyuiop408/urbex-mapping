import tomlkit
"""
https://toml.io/en/v1.0.0#array-of-tables
https://www.toml-lint.com/
https://tomlkit.readthedocs.io/en/latest/api/

x = get_crawler_index("https://www.28dayslater.co.uk/forum/", conf)
y = get_sub_index("solomon.123/", conf["crawler"]["xenforo"][x])
"""

class config:
    FILE = "config.cfg"
    def __init__(self):
        self.load()
        return

    def load(self):
        with open(self.FILE, mode="rt", encoding="utf-8") as f:
            self.cfg = tomlkit.load(f)

    def save(self):
        with open(self.FILE, mode="r+t", encoding="utf-8") as fp:
            fp.write(tomlkit.dumps(self.cfg))
        return
    

    #get the index of the crawler in the config using the sites url. returns -1 if not found
    def get_crawler_index(self, site, crawler="xenforo"):
        self.load()
        x = self.cfg["crawler"][crawler]
        for count, value in enumerate(x):
            if value.get("url") == site:
                return count
        return -1

    #get the index of the section for crawler section. returns -1 if not found
    def get_sub_index(sub):
        self.load()
        for count, value in enumerate(self.cfg["subs"]):
            if value[0] == sub:
                return count
        return -1