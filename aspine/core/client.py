import logging
import sys
import time
import datetime
import signal

from multiprocessing.managers import SyncManager


class AspineClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 5116, authkey: str = "123456", *args, **kwargs):
        logging.debug(f"Start initializing client at {datetime.datetime.now()}")
        self.core = SyncManager(
            (host, port),
            authkey=authkey.encode()
        )

    def connect(self):
        try:
            self.core.connect()
            self.core.register("get_mem_data")
            self.core.register("get_manager_info")

            self._get_mem_data = getattr(self.core, "get_mem_data")
            self._get_manager_info = getattr(self.core, "get_manager_info")

        except ConnectionRefusedError as cre:
            logging.error(f"Please check server/manager is up and running.")
            logging.exception(cre)

    def get(self, key_name):
        try:
            # self._get_mem_data()._close()
            res = self._get_mem_data().get(key_name)
            if res is not None:
                return res
        except Exception as e:
            logging.error(f"Error.")
            logging.exception(e)

    def set(self, key_name, value):
        try:

            res = {key_name: {
                "name": key_name,
                "value": value,
                "set_ts": time.time()
            }}
            # self._get_mem_data()._close()
            self._get_mem_data().update(res)
        except Exception as e:
            logging.error(f"Error.")
            logging.exception(e)

    def is_exist(self, key_name):
        try:
            r = self.get(key_name)
            if r is not None:
                return True
            else:
                return False
        except Exception as e:
            logging.error(f"Error.")
            logging.exception(e)