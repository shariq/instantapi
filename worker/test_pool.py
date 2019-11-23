import replayer
import time
import threading

# use pool = replayer.Pool() normally!
# DummyWorker is just for testing
pool = replayer.Pool(replayer.DummyWorker)

pool.run_job('job1')
pool.run_job('job2')
pool.run_job('job3')
pool.run_job('job4')
time.sleep(10)
threading.Thread(target=pool.run_job, args=('job5', )).start()
threading.Thread(target=pool.run_job, args=('job6', )).start()
threading.Thread(target=pool.run_job, args=('job7', )).start()
threading.Thread(target=pool.run_job, args=('job8', )).start()
threading.Thread(target=pool.run_job, args=('job9', )).start()
time.sleep(10)
threading.Thread(target=pool.run_job, args=('job10', )).start()
threading.Thread(target=pool.run_job, args=('job11', )).start()
threading.Thread(target=pool.run_job, args=('job12', )).start()
