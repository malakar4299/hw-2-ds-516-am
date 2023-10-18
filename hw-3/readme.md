# Project: Logging Forbidden Requests

This project consists of several applications designed to generate, handle, and log forbidden or banned requests. The applications include a tool to generate requests to a specific domain, a Flask application to handle incoming requests and log forbidden ones, and a continuous listener to process messages from Google Pub/Sub.

## Applications Overview

1. **Request Generator**: This Python application generates HTTP requests with specific headers to simulate requests from different countries, genders, ages, and income brackets.

2. **Flask Application (File Server)**: A Flask application that serves files and checks for forbidden requests based on the country specified in the headers. Forbidden requests are logged and published to a Google Pub/Sub topic.

3. **Flask Application (Forbidden Requests Logger)**: This application consists of an HTTP endpoint that logs forbidden requests directly and a continuous listener that pulls messages from a Google Pub/Sub subscription detailing forbidden requests.

## Steps to Recreate and Run the Application

1. **Clone the Repository**:
   - Use your local laptop or Google Cloud Shell to clone the GitHub repository.
     ```
     git clone <REPOSITORY_URL>
     ```
     Replace `<REPOSITORY_URL>` with the actual URL of the repository.

2. **Deploy the Flask Application to Google Cloud Functions**:
   - Navigate to the directory containing the Flask application (assuming it's the root of the cloned repository).
     ```
     cd <PATH_TO_REPOSITORY>
     ```
   - Deploy the application using the following command:
     ```
