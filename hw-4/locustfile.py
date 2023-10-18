from locust import HttpUser, task, between

class MyUser(HttpUser):
    wait_time = between(1, 2)  # Users wait between 1 and 2 seconds between tasks

    @task
    def get_html_page(self):
        self.client.get("/4556.html")
