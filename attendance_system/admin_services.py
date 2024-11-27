from flask import Flask
from flask.logging import default_handler
import logging
import requests
from datetime import datetime


class DiscordHandler(logging.StreamHandler):

    def __init__(self, url):
        super(DiscordHandler, self).__init__()
        self.url = url
        now = datetime.now().strftime('%Y.%m.%d-%H%M%S')
        self.file = f"./attendance_system/logs/logging_{now}.log"

    def emit(self, record):
        msg = self.format(record)
        self.send_message(msg)

    def send_message(self, text):
        message = {
            'content': text,
        }

        requests.post(self.url, json=message)

        # ログをファイルに出力する
        with open(self.file, "a") as f:
            f.write(text + "\n")
