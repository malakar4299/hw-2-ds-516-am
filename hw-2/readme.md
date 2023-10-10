# How to Run the Program for a New User

_Note: The same information has been posted to the GitHub README file._

## Steps to Run the Program

1. **Clone the GitHub Repository**:  git clone https://github.com/malakar4299/hw-2-ds-561-am.git into your desired directory.

2. **File Availability**:  
The files may not be present in the folder initially, but you can find them in the bucket `gs://hw-2-files-bucket/files`.

3. **Generating Files**:  
If you need to generate files, run: python generator.py

4. **Credentials Requirement**:  
To execute the page-rank algorithm, you'll require the necessary credentials. Anonymous access has been disabled for security reasons. To obtain the service account credentials JSON file, email me. Once you receive it, paste the JSON file into the root directory of the cloned repository.

5. **Executing the Page-Rank Algorithm**:  
Run the command: python page-rank.py

This should generate the page rank and display the output on the terminal.

6. **Logs**:  
The `logs.json` file retains the runtime information, including the latest page-rank generation details.

## Function Descriptions and Details

- **read_last_run_time(types, filename="logs.json")**:  
Reads the last run time from the `logs.json` file. The `type` parameter determines whether it's the processing time or upload time.

- **write_run_info(elapsed_upload_time, elapsed_processing_time, incoming_stats, outgoing_stats, top_5_counts, filename="logs.json")**:  
Logs new data into `logs.json` and regenerates the file as required.

- **upload_blob(bucket_name, source_file_name, destination_blob_name)**:  
Uploads blobs to the specified bucket. Source and destination file names define the blob specifics.

- **upload_folder_to_gcs(bucket_name, folder_path)**:  
Recursively uploads an entire folder to the bucket, treating each file as a distinct blob.

- **class LinkExtractor(HTMLParser)**:  
A custom class to extract `<a href>` tags from files to determine outgoing links.

- **pagerank(graph, max_iter=10, damping=0.85, tol=0.005)**:  
This is the core algorithm to compute page rank. It has default settings for max iterations (10), damping (0.85), and tolerance (0.005). In practice, while the assignment specifies certain values, the damping factor is typically provided, and the default page rank is calculated based on it.

- **process_blob_data(blob)**:  
Processes individual blob data.

- **compute_stats(link_counts)**:  
Calculates stats based on the provided link counts.

- **Main**:  
The primary function that orchestrates the execution of all sub-functions.




