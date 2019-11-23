import replayer
import time
import threading

worker = replayer.Droplet()

while worker.status != 'available':
    time.sleep(5)

time.sleep(20)
