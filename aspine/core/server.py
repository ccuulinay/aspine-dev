import logging
import sys
import time
import datetime
import signal

from multiprocessing.managers import SyncManager


class AspineServer:

    def __init__(self, host: str = "127.0.0.1", port: int = 5116, authkey: str = "123456", *args, **kwargs):
        logging.debug(f"Start initializing manager at {datetime.datetime.now()}")

        class HelperManager(SyncManager):
            pass

        self.mem_data = {}
        self.manager_info = {
            "app_name": "A-spine data store",
            "start_time": datetime.datetime.now()
        }

        def get_mem_data():
            return self.mem_data

        def get_manager_info():
            return self.manager_info

        HelperManager.register("get_mem_data", get_mem_data)
        HelperManager.register("get_manager_info", get_manager_info)
        self.manager = HelperManager(
            (host, port),
            authkey=authkey.encode()
        )

    def __shutdown_manager__(self, signum, frame):

        logging.info(f"Capture signal with number: {signum}")
        logging.info(f"Existing manager gracefully.")
        logging.info(f"Shutting down.")
        self.manager.shutdown()
        sys.exit(0)

    def stop(self):
        self.manager.shutdown()
        return self.manager

    def start(self):
        signal.signal(signal.SIGINT, self.__shutdown_manager__)
        signal.signal(signal.SIGTERM, self.__shutdown_manager__)
        self.manager.start()
        return self.manager

    def run(self):
        signal.signal(signal.SIGINT, self.__shutdown_manager__)
        signal.signal(signal.SIGTERM, self.__shutdown_manager__)
        self.manager.get_server().serve_forever()