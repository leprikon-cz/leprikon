import time
import traceback

from django.core.management.base import BaseCommand
from django.utils.translation import activate
from requests import get
from requests.exceptions import ConnectionError

from leprikon.conf import settings
from leprikon.rocketchat import RocketChat


class Command(BaseCommand):
    help = "Sync all users, groups and settings with RocketChat"

    def handle(self, *args, **options):
        rocket_chat_ready = False
        while not rocket_chat_ready:
            try:
                rocket_chat_ready = get(settings.ROCKETCHAT_API_URL).ok
            except ConnectionError as e:
                self.stdout.write(self.style.ERROR(repr(e)))
                self.stdout.write(f"Waiting for RocketChat at {settings.ROCKETCHAT_API_URL}")
                time.sleep(5)
        activate(settings.LANGUAGE_CODE)
        rc = RocketChat()
        self.call(rc.configure)
        self.call(rc.sync_roles)
        self.call(rc.sync_users)
        self.call(rc.sync_subjects)

    def call(self, func):
        self.stdout.write(f"calling RocketChat.{func.__name__}")
        try:
            result = func()
        except Exception:
            self.stdout.write(self.style.ERROR("failed"))
            traceback.print_exc()
        else:
            self.stdout.write(self.style.SUCCESS(f"OK ({repr(result)})"))
