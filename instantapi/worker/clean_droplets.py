import replayer
import time
import threading

import sys

droplets = replayer.Droplet.list_all_droplets()
print(droplets)

bad_droplets = [
    droplet for droplet in droplets if "instantapi-worker-" in droplet["name"]
]

print(bad_droplets, bad_droplets)

response = str(input("are you sure you want to destroy all the above? (say YES): "))
if response != "YES":
    sys.exit(-1)

for droplet in bad_droplets:
    replayer.Droplet.destroy_droplet(droplet["id"])
