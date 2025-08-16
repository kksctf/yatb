#!/usr/bin/env python3
# just a very simple builder

from cyclopts import App

app = App("example task builder")


@app.command()
def main():
    print("Hello!")


if __name__ == "__main__":
    app()
