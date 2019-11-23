"""
Pool of DigitalOcean droplets which have Selenium running on them.
A way to distribute the work to those droplets.
55 minutes after spinning up a droplet, if the pool is less than 50% full spin it down. Or include this in the user script for the droplet.
Since the droplet is up for a while, it can have a user script run on it. This would be the initialization stage for a worker. Then this is pretty general and other people can use it easily!!!
"""

import time
import threading
import random
import requests
import json
import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from types import ModuleType

from selenium.webdriver.remote.remote_connection import LOGGER

LOGGER.setLevel(logging.WARNING)

from selenium import webdriver

# change this line to stop the module from verbose printing. import logging is too annoying
verbose_print = lambda s: print(s)
# verbose_print = lambda s: s


class DummyWorker:
    def __init__(self, pool):
        self.last_considered_destruction = time.time()
        self.status = "initializing"
        self.job_time = None
        self.id = "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for c in range(8))

        verbose_print("initializing new droplet {}".format(self))

        def slow_create(self):
            time.sleep(2)
            self.status = "available"
            verbose_print("initialized {}".format(self))

        threading.Thread(target=slow_create, args=(self,), daemon=True).start()

    def do_job(self, params):
        if self.status != "available":
            print("FAILURE: tried to do a job on an unavailable worker {}".format(self))
        self.status = "working"
        self.job_params = params
        self.job_time = time.time()
        verbose_print("job sent to {} with params {}".format(self, params))
        time.sleep(5)
        self.status = "available"
        return self.job_params + " -> resultss"

    def destroy(self):
        verbose_print("destroyed {}".format(self))
        pass

    def __str__(self):
        return "<worker id={} status={} job_time={}>".format(
            self.id, self.status, self.job_time
        )

    def __repr__(self):
        return str(self)


DIGITALOCEAN_TOKEN = open("DIGITALOCEAN_TOKEN").read().strip()
DIGITALOCEAN_TAG = "instantapi"


class Droplet:
    def __init__(self, pool=None):
        self.pool = pool
        self.last_considered_destruction = time.time()
        self.status = "initializing"
        self.job_time = None
        self.id = "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for c in range(8))
        self.droplet_id = None
        self.ip_address = None

        verbose_print("initializing new droplet {}".format(self))

        def slow_create(self):
            # curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" -d '{"name":"example.com","region":"nyc3","size":"s-1vcpu-1gb","image":"ubuntu-16-04-x64","ssh_keys":[107149],"backups":false,"ipv6":true,"user_data":null,"private_networking":null,"volumes": null,"tags":["web"]}' "https://api.digitalocean.com/v2/droplets"

            url = "https://api.digitalocean.com/v2/droplets"

            user_data = """#!/bin/bash

apt-get -y update
apt-get -y install docker.io
sleep 10
docker run --shm-size=200m -d -p 4444:4444 selenium/standalone-chrome
"""

            payload = {
                "name": "{}-worker-{}".format(DIGITALOCEAN_TAG, self.id),
                "region": "sfo2",
                "size": "s-1vcpu-1gb",
                "image": "ubuntu-18-04-x64",
                "ssh_keys": Droplet.get_ssh_keys(),
                "backups": False,
                "ipv6": False,
                "user_data": user_data,
                "private_networking": None,
                "volumes": None,
                "tags": ["{}-worker".format(DIGITALOCEAN_TAG)],
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(DIGITALOCEAN_TOKEN),
            }

            response = requests.post(url, data=json.dumps(payload), headers=headers)
            self.droplet_id = response.json()["droplet"]["id"]

            ip_address = Droplet.get_ip_address(self.droplet_id)
            while ip_address is None:
                time.sleep(5)
                ip_address = Droplet.get_ip_address(self.droplet_id)

            time.sleep(10)

            self.ip_address = ip_address
            verbose_print("ip_address={}".format(self.ip_address))

            self.container_remote = "http://{}:4444/wd/hub".format(self.ip_address)

            opts = Options()
            opts.add_argument(
                "user-agent=Mozilla/5.0 (Android 4.4; Tablet; rv:41.0) Gecko/41.0 Firefox/41.0"
            )
            capabilities = webdriver.DesiredCapabilities.CHROME.copy()
            capabilities.update(opts.to_capabilities())

            self.driver = None
            for i in range(40):
                verbose_print("{}th attempt to connect to driver on {}".format(i, self))
                try:
                    driver = webdriver.Remote(self.container_remote, capabilities)
                    self.driver = driver
                    break
                except Exception:
                    time.sleep(3)

            if self.driver is None:
                verbose_print(
                    "failed to connect to driver on {}, destroying..".format(self)
                )
                self.destroy()
                return

            self.status = "available"
            verbose_print("initialized {}".format(self))

        threading.Thread(target=slow_create, args=(self,), daemon=True).start()

    def do_job(self, params):
        if self.status != "available":
            print("FAILURE: tried to do a job on an unavailable worker {}".format(self))
        self.status = "working"
        self.job_params = params
        self.job_time = time.time()
        verbose_print("job sent to {} with params {}".format(self, params))
        content = params["content"]
        code = "\n".join(content.split("\n")[2:])
        class_name = "TestDefaultSuite"
        module_name = "fake_module_name"
        compiled = compile(code, "<string>", "exec")
        module = ModuleType(module_name)
        exec(compiled, module.__dict__)
        t = (module.__dict__[class_name])()
        # CURIOSITY: do drivers die occasionally and need to be resuscitated? that would break this abstraction..
        t.driver = self.driver
        t.test_findSamsung()
        screenshot_path = (
            "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for c in range(10))
            + ".png"
        )
        page_source = self.driver.page_source
        self.driver.save_screenshot(screenshot_path)
        results = {"page_source": page_source, "screenshot_path": screenshot_path}
        self.status = "available"
        return results

    def destroy(self):
        if self.pool and self in self.pool.workers:
            self.pool.workers.remove(self)
        self.status = "dead"
        verbose_print("destroyed {}".format(self))
        self.destroy_droplet(self.droplet_id)

    @staticmethod
    def destroy_droplet(droplet_id):
        # send a request to destroy the droplet on digitalocean
        # curl -X DELETE -H "Content-Type: application/json" -H "Authorization: Bearer b7d03a6947b217efb6f3ec3bd3504582" "https://api.digitalocean.com/v2/droplets/3164494"
        url = "https://api.digitalocean.com/v2/droplets/{}".format(droplet_id)
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(DIGITALOCEAN_TOKEN),
        }
        requests.delete(url, headers=headers)

    @staticmethod
    def list_all_droplets():
        # get a list of all d.o. droplets names
        # curl -X GET -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" "https://api.digitalocean.com/v2/droplets?page=1&per_page=1"

        url = "https://api.digitalocean.com/v2/droplets"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(DIGITALOCEAN_TOKEN),
        }
        page_number = 1

        response = requests.get(
            url, params={"page": page_number, "per_page": 50}, headers=headers
        )
        response_json = response.json()
        droplets = [
            {"id": droplet["id"], "name": droplet["name"]}
            for droplet in response_json["droplets"]
        ]

        while response_json.get("links", {}).get("pages", {}).get("next", {}):
            page_number += 1
            response = requests.get(
                url, params={"page": page_number, "per_page": 50}, headers=headers
            )
            response_json = response.json()
            droplets.extend(
                [
                    {"id": droplet["id"], "name": droplet["name"]}
                    for droplet in response_json["droplets"]
                ]
            )

        return droplets

    @staticmethod
    def get_ip_address(droplet_id):
        # get the ip address of the droplet
        # curl -X GET -H "Content-Type: application/json" -H "Authorization: Bearer b7d03a6947b217efb6f3ec3bd3504582" "https://api.digitalocean.com/v2/droplets/3164494"

        url = "https://api.digitalocean.com/v2/droplets/{}".format(droplet_id)
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(DIGITALOCEAN_TOKEN),
        }

        response = requests.get(url, headers=headers)
        ipv4_addresses = (
            response.json().get("droplet", {}).get("networks", {}).get("v4", {})
        )

        if ipv4_addresses:
            return ipv4_addresses[0]["ip_address"]

    @staticmethod
    def get_ssh_keys():
        # get all the ssh keys on this d.o. account
        # curl -X GET -H "Content-Type: application/json" -H "Authorization: Bearer $TOKEN" "https://api.digitalocean.com/v2/account/keys"

        url = "https://api.digitalocean.com/v2/account/keys"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(DIGITALOCEAN_TOKEN),
        }

        response = requests.get(url, headers=headers)
        response_json = response.json()
        ssh_keys = [int(ssh_key["id"]) for ssh_key in response_json["ssh_keys"]]

        return ssh_keys

    def __str__(self):
        return "<worker id={} status={} ip={}>".format(
            self.id, self.status, self.ip_address
        )

    def __repr__(self):
        return str(self)


SPIN_DOWN_THRESHOLD = 0.3  # if there's less than this utilization, spin down
SPIN_UP_THRESHOLD = 0.8  # if there's more than this utilization, spin up
MIN_WORKERS = 3  # the min number of workers to always keep on


class Pool:
    def __init__(self, worker_class=Droplet):
        self.worker_class = worker_class
        self.workers = []
        self.jobs = []
        self.rebalancer = threading.Thread(target=self.rebalance, daemon=True)
        self.rebalancer.start()

    def create_worker(self):
        worker = self.worker_class(self)
        self.workers.append(worker)
        return worker

    def get_free_worker(self):
        for worker in self.workers:
            if worker.status == "available":
                return worker
        return None

    def destroy_worker(self, worker):
        worker.destroy()
        if worker in self.workers:
            self.workers.remove(worker)
        worker.status = "dead"

    def rebalance(self):
        while True:
            if len(self.workers) < MIN_WORKERS:
                new_workers = MIN_WORKERS - len(self.workers)
                print(
                    "len(self.workers) < MIN_WORKERS; creating {} new workers".format(
                        new_workers
                    )
                )
                for i in range(new_workers):
                    self.create_worker()

            working_workers = [worker.status for worker in self.workers].count(
                "working"
            )
            utilization = float(working_workers) / len(self.workers)
            for worker in self.workers:
                if (
                    worker.status == "available"
                    and time.time() - worker.last_considered_destruction > 58 * 60
                ):
                    # useless to destroy a worker before ~1 hour elapses, since you get charged for the whole hour anyways
                    if utilization < SPIN_DOWN_THRESHOLD and num_workers > MIN_WORKERS:
                        print(
                            "destroying worker {}; utilization < SPIN_DOWN_THRESHOLD and num_workers > MIN_WORKERS".format(
                                worker
                            )
                        )
                        self.destroy_worker(worker)
                    worker.last_considered_destruction += 60 * 60

            working_workers = [worker.status for worker in self.workers].count(
                "working"
            )
            utilization = float(working_workers) / len(self.workers)
            if utilization > SPIN_UP_THRESHOLD:
                new_utilization = utilization
                new_workers = 0
                while new_utilization > SPIN_UP_THRESHOLD:
                    new_workers += 1
                    new_utilization = float(working_workers) / (
                        len(self.workers) + new_workers
                    )
                print(
                    "utilization > SPIN_UP_THRESHOLD; creating {} new workers".format(
                        new_workers
                    )
                )
                for i in range(new_workers):
                    self.create_worker()

            time.sleep(60)

    def run_job(self, params):
        worker = (
            self.get_free_worker()
        )  # returns None if no workers are available; should rarely ever happen
        while worker is None:
            print("had to manually spin up a new worker!")
            worker = self.create_worker()
            while worker.status == "initializing":
                time.sleep(5)
            time.sleep(2)
            if worker.status == "dead" or worker not in self.workers:
                worker = None
        return worker.do_job(params)

    def async_run_job(self, params, start_callback, end_callback, error_callback):
        def async_func():
            try:
                start_callback()
                result = self.run_job(params)
                end_callback(result)
            except Exception as err:
                error_callback(err)

        threading.Thread(target=async_func, daemon=True).start()
