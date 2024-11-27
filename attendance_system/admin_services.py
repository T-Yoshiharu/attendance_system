from flask import Flask
from flask.logging import default_handler
import logging
import requests


class DiscordHandler(logging.StreamHandler):

    def __init__(self, url):
        super(DiscordHandler, self).__init__()
        self.url = url

    def emit(self, record):
        msg = self.format(record)
        self.send_message(msg)

    def send_message(self, text):
        message = {
            'content': text,
        }

        requests.post(self.url, json=message)
