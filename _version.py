VERSION = "1.1.0"


def get_version():
    return VERSION


def set_version(new_version):
    global VERSION
    VERSION = new_version


if __name__ == "__main__":
    print(get_version())