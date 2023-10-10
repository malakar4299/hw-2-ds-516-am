import os
import re
from html.parser import HTMLParser
from collections import defaultdict
import numpy as np
from google.cloud import storage
from google.oauth2 import service_account
import json
import time
import concurrent.futures

f = open('ds-561-am-cc3cb4be64ff.json')
creds = json.load(f)


credentials = service_account.Credentials.from_service_account_info(creds)

def read_last_run_time(types,filename="logs.json"):
    try:
        with open(filename, "r") as f:
            data = f.read()
            if not data:
                return None  # File is empty
            data_json = json.loads(data)
            return data_json.get(types + '_time', None)
    except (FileNotFoundError, json.JSONDecodeError):
        return None  # File not found or invalid JSON

def write_run_info(elapsed_upload_time,elapsed_processing_time, incoming_stats, outgoing_stats, top_5_counts, filename="logs.json"):
    with open(filename, "w") as f:
        data = {'upload_time': elapsed_upload_time}
        data['processing_time'] = elapsed_processing_time
        # incoming_stats["Quintiles"] = incoming_stats["Quintiles"].tolist()
        # outgoing_stats["Quintiles"] = outgoing_stats["Quintiles"].tolist()
        # data['incoming_stats'] = incoming_stats
        # data['outgoing_stats'] = outgoing_stats
        # data['top_5_pages'] = top_5_counts
        json.dump(data, f)

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    storage_client = storage.Client.create_anonymous_client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print(f"File {source_file_name} uploaded to {destination_blob_name}.")

def upload_folder_to_gcs(bucket_name, folder_path):
    storage_client = storage.Client.create_anonymous_client()
    bucket = storage_client.get_bucket(bucket_name)

    count = 0

    last_run_time = read_last_run_time("upload","logs.json")

    if last_run_time is not None:
        print(f"Please note, this could take some time. Last run took {last_run_time} seconds.")

    start_time = time.time()

    for root, _, files in os.walk(folder_path):
        for file in files:
            local_file = os.path.join(root, file)
            remote_path = os.path.relpath(local_file, folder_path)

            # Check if blob already exists
            blob = bucket.blob('files/'+remote_path)
            if not blob.exists():
                blob.upload_from_filename(local_file)
                count+=1
            else:
                break

    end_time = time.time()
    elapsed_time = end_time - start_time

    write_run_info(elapsed_time,read_last_run_time('processing'), {}, {}, {})

    print(f"{count} files uploaded")

# Custom parser to extract links
class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for name, value in attrs:
                if name == "href":
                    self.links.append(value)





def pagerank(graph, max_iter=10, damping=0.85, tol=0.005):
    num_pages = len(graph)
    pr = {page: 1/num_pages for page in graph}
    base_pr = (1 - damping) / num_pages

    for _ in range(max_iter):
        next_pr = {page: base_pr for page in graph}
        for page, outgoing_links in graph.items():
            if not outgoing_links:
                continue  # Skip this page because it has no outgoing links

            share_pr = pr[page] / len(outgoing_links)
            for link in outgoing_links:
                if link not in next_pr:
                    next_pr[link] = base_pr
                next_pr[link] += share_pr * damping
        
        # Check for convergence
        diff = sum(abs(next_pr[page] - pr[page]) for page in graph)
        if diff < tol:
            break
        
        pr = next_pr

    return pr

def process_blob_data(blob):
    """Processes a blob and extracts links."""
    filename = blob.name.replace("files/", "").replace(".html", "")
    parser = LinkExtractor()

    with blob.open("r") as f:
        parser.feed(f.read())

    links = {re.sub(r"\.html$", "", link) for link in parser.links}
    return filename, links


def compute_stats(link_counts):
    return {
        "Average": np.mean(link_counts),
        "Median": np.median(link_counts),
        "Max": max(link_counts),
        "Min": min(link_counts),
        "Quintiles": np.percentile(link_counts, [20, 40, 60, 80])
    }


def main():
    graph = defaultdict(set)
    out_count = defaultdict(int)

    storage_client = storage.Client.create_anonymous_client()
    bucket_name = "hw-2-files-bucket"

    folder_path = "./files"  

    upload_folder_to_gcs(bucket_name, folder_path)

    last_run_time = read_last_run_time("processing","logs.json")

    if last_run_time is not None:
        print(f"Please note, this could take some time. Last web run took {last_run_time} seconds.")

    start_time = time.time()


    bucket = storage_client.bucket(bucket_name)
    blobs = list(bucket.list_blobs())

    out_count = defaultdict(int)

    BATCH_SIZE = 100
    total_blobs = len(blobs)

    for i in range(0, total_blobs, BATCH_SIZE):
        batch = blobs[i:i+BATCH_SIZE]

        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(process_blob_data, batch))

            for filename, links in results:
                graph[filename] = links
                out_count[filename] = len(links)

    in_count = [len(graph[filename]) for filename in graph]
    out_count = [out_count[filename] for filename in graph]

    print("Incoming links stats:", compute_stats(in_count))
    print("Outgoing links stats:", compute_stats(out_count))

    pr = pagerank(graph)
    top_5_pages = sorted(pr, key=pr.get, reverse=True)[:5]
    print("Top 5 pages by PageRank:", top_5_pages)

    end_time = time.time()

    write_run_info(read_last_run_time('upload'), end_time, compute_stats(in_count), compute_stats(out_count), top_5_pages)


if __name__ == "__main__":
    main()
