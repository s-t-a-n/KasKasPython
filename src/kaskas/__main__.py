""" main entrypoint for `jasjas`. """

from _jasjas.app.app import Application as JasJasApplication


def main():
    JasJasApplication().run()


if __name__ == "__main__":
    main()
