"""
Main module for daemon
"""

import os
import time
import requests
import traceback

import klotio

class Daemon:
    """
    Main class for daemon
    """

    def __init__(self):

        self.sleep = float(os.environ['SLEEP'])

        self.chore_api = os.environ['CHORE_API']

        self.logger = klotio.logger("nandy-io-chore-daemon")

        self.logger.debug("init", extra={
            "init": {
                "sleep": self.sleep,
                "chore_api": self.chore_api
            }
        })

    @staticmethod
    def expire(data):
        """
        Determines if there's a need to expire
        """

        now = time.time()

        # If it has an expires and it's been more than that much time

        if "expires" in data and data["expires"] + data["start"] < now:
            return True

        return False

    @staticmethod
    def remind(data):
        """
        Determines if there's a need to remind
        """

        now = time.time()

        # If it has a delay and isn't time yet, don't bother yet

        if "delay" in data and data["delay"] + data["start"] > now:
            return False

        # If it's paused, don't bother either

        if data.get("paused"):
            return False

        # If it has an interval and it's more been more than that since the last notification

        if "interval" in data and now > data["notified"] + data["interval"]:
            return True

        return False

    def tasks(self, routine):
        """
        Sees if any reminders need to go out for a task of a routine
        """

        for task in routine["data"]["tasks"]:

            self.logger.info("task", extra={"task": task})

            if "start" in task and "end" not in task:

                if self.remind(task):
                    self.logger.info("remind")
                    requests.patch(f"{self.chore_api}/routine/{routine['id']}/task/{task['id']}/remind").raise_for_status()

                break

    def routine(self, routine):
        """
        Sees if any reminders need to go out for a routine
        """

        self.logger.info("routine", extra={"routine": routine})

        if self.expire(routine["data"]):
            self.logger.info("expire")
            requests.patch(f"{self.chore_api}/routine/{routine['id']}/expire").raise_for_status()
            return

        if self.remind(routine["data"]):
            self.logger.info("remind")
            requests.patch(f"{self.chore_api}/routine/{routine['id']}/remind").raise_for_status()

        if "tasks" in routine["data"]:
            self.tasks(routine)

    def process(self):
        """
        Processes all the routines for reminding
        """

        for routine in requests.get(f"{self.chore_api}/routine?status=opened").json()["routines"]:
            try:
                self.routine(routine)
            except Exception as exception:
                print(str(exception))
                print(traceback.format_exc())

    def run(self):
        """
        Runs the daemon
        """

        while True:
            self.process()
            time.sleep(self.sleep)
