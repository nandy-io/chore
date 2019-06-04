"""
Main module for daemon
"""

import os
import time
import requests
import traceback

class Daemon(object):
    """
    Main class for daemon
    """

    def __init__(self):

        self.sleep = float(os.environ['SLEEP'])

        self.chore = os.environ['CHORE_API']

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

            if "start" in task and "end" not in task:
                
                if self.remind(task):

                    requests.patch(f"{self.chore}/routine/{routine['id']}/task/{task['id']}/remind").raise_for_status()

                break

    def routine(self, routine):
        """
        Sees if any reminders need to go out for a routine
        """

        if self.expire(routine["data"]):
            requests.patch(f"{self.chore}/routine/{routine['id']}/expire").raise_for_status()
            return

        if self.remind(routine["data"]):
            requests.patch(f"{self.chore}/routine/{routine['id']}/remind").raise_for_status()

        if "tasks" in routine["data"]:
            self.tasks(routine)

    def process(self):
        """
        Processes all the routines for reminding
        """

        for routine in requests.get(f"{self.chore}/routine?status=opened").json()["routines"]:

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
