import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import re
import os
import logging


logging.getLogger().setLevel(logging.INFO)


class LogElements(beam.DoFn):
    def process(self, element):
        logging.info(element)
        yield element

# Define your pipeline options
options = PipelineOptions(
    runner='DataflowRunner',  # Change to 'DirectRunner' for local testing or DataflowRunner for prod
    project='ds-561-am',
    temp_location='gs://hw-2-files-bucket/files',
    region='us-central1'
)



class ExtractLinks(beam.DoFn):
    def process(self, element):
        # Regular expression to find links
        LINK_PATTERN = re.compile(r'<a\s+(?:[^>]*?\s+)?href="(\d+\.html)"', re.IGNORECASE)
        # Extract the file name and the links
        file_name, content = element
        links = LINK_PATTERN.findall(content)
        return [(file_name, link) for link in links]

def format_result(element):
    file, link_count = element
    return f'{file}: {link_count} links'

# Testing code, not for all files. Only usable for 5 files part. Uncomment if testing
# class ReadFile(beam.DoFn):
#     def process(self, file_path):
#         with beam.io.filesystems.FileSystems.open(file_path) as file:
#             contents = file.read().decode('utf-8')
#             yield file_path, contents

def run():

    # Testing code please keep commented unless want to test pipeline (FOR TA's)
    # files_to_read = [
    #     'gs://hw-2-files-bucket/files/0.html',
    #     'gs://hw-2-files-bucket/files/1.html',
    #     'gs://hw-2-files-bucket/files/2.html',
    #     'gs://hw-2-files-bucket/files/3.html',
    #     'gs://hw-2-files-bucket/files/4.html'
    # ]

    with beam.Pipeline(options=options) as pipeline:
        # Read files from Google Cloud Storage
        
        # Production code, not for testing. Please comment if testing for just 5 files above
        files_content = (
            pipeline 
            | 'ReadFiles' >> beam.io.ReadFromTextWithFilename('gs://hw-2-files-bucket/files/*')
            | 'ExtractLinks' >> beam.ParDo(ExtractLinks())
        )


        # Testing code, please keep commented
        # Create a PCollection of file paths
        # file_paths = pipeline | 'CreateFileList' >> beam.Create(files_to_read)

        # Read contents of each file
        # files_content = (
        #     file_paths
        #     | 'ReadFiles' >> beam.ParDo(ReadFile())
        #     | 'ExtractLinks' >> beam.FlatMap(extract_links)
        # )


        # Count outgoing links
        outgoing_links_count = (
            files_content
            | 'CountOutgoing' >> beam.combiners.Count.PerKey()
            | 'LogOutgoingCounts' >> beam.ParDo(LogElements())
            | 'FormatOutgoing' >> beam.Map(format_result)
            | 'GetTop5Outgoing' >> beam.transforms.combiners.Top.Of(5, key=lambda x: x[1])
            | 'WriteTopOutgoing' >> beam.io.WriteToText('gs://hw-2-files-bucket/files/output/prod/top_outgoing')
        )

        # Count incoming links
        incoming_links_count = (
            files_content
            | 'MapToIncoming' >> beam.Map(lambda x: (x[1], x[0]))  # Swap to count incoming
            | 'CountIncoming' >> beam.combiners.Count.PerKey()
            | 'LogIncomingCounts' >> beam.ParDo(LogElements())
            | 'FormatIncoming' >> beam.Map(format_result)
            | 'GetTop5Incoming' >> beam.transforms.combiners.Top.Of(5, key=lambda x: x[1])
            | 'WriteTopIncoming' >> beam.io.WriteToText('gs://hw-2-files-bucket/files/output/prod/top_incoming')
        )

if __name__ == '__main__':
    run()
