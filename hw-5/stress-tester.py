import requests
import time
import multiprocessing
import threading
import matplotlib.pyplot as plt

def make_request(url):
    try:
        response = requests.get(url)
        # Return the time taken to get the response
        return response.elapsed.total_seconds()
    except requests.RequestException:
        return None
    
def worker(target_url, num_requests_per_thread, response_times, success_count, failure_count, first_failure_at):
    for i in range(num_requests_per_thread):
        response_time = make_request(target_url)
        response_times.append(response_time)
        if response_time is None:
            failure_count.value += 1
            if first_failure_at.value == 0:
                first_failure_at.value = i + 1
        else:
            success_count.value += 1

def stress_test(target_url, num_requests, num_threads):
    # Create a Manager object to manage shared data across processes
    manager = multiprocessing.Manager()
    response_times = manager.list()  # Shared list among processes
    success_count = manager.Value('i', 0)  # Shared integer among processes
    failure_count = manager.Value('i', 0)  # Shared integer among processes
    first_failure_at = manager.Value('i', 0)  # Shared integer among processes

    # Create and start multiple processes
    processes = []
    for _ in range(num_threads):
        p = multiprocessing.Process(target=worker, args=(target_url, num_requests // num_threads, response_times, success_count, failure_count, first_failure_at))
        processes.append(p)
        p.start()

    # Wait for all processes to finish
    for p in processes:
        p.join()

    # Process the collected data
    total_requests = success_count.value + failure_count.value
    print(f"Total requests made: {total_requests}")
    print(f"Successful requests: {success_count.value}")
    print(f"Failed requests: {failure_count.value}")
    if first_failure_at.value:
        print(f"First failure at request number: {first_failure_at.value}")
    
    # Plot the response times
    plt.hist(response_times, bins=50, color='blue', edgecolor='black')
    plt.title("Response Times")
    plt.xlabel("Time (ms)")
    plt.ylabel("Number of Requests")
    plt.savefig('response_times.png')  # Save the plot to a file
    #plt.show()  # If you also want to display the plot

if __name__ == '__main__':
    multiprocessing.freeze_support()
    target_url = "http://35.209.14.129/4556.html"
    num_requests = 1000
    num_threads = 100
    stress_test(target_url, num_requests, num_threads)