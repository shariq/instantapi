import replayer
import time
import threading

print('initial droplets ->', replayer.Droplet.list_all_droplets())
worker = replayer.Droplet()
print('just initialized droplet; waiting...', 'worker=', worker)
time.sleep(20)
print('waited 20s after creating a new droplet ->', replayer.Droplet.list_all_droplets(), 'worker=', worker)
worker.destroy()
print('just destroyed the droplet...', 'worker=', worker)
time.sleep(20)
print('destroyed the droplet and waited 20s ->', replayer.Droplet.list_all_droplets(), 'worker=', worker)

# replayer.Droplet.destroy_droplet(168344859)
