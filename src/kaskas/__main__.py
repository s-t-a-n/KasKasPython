""" main entrypoint for `kaskas`. """

from _kaskas.app import Application as KasKasApplication


def main():
    KasKasApplication().run()


if __name__ == "__main__":
    main()
