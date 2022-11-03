from time import sleep
from docker.errors import APIError, NotFound
from docker.models.containers import Container


class TempDockerContainer(Container):
    """ Temporarily keeps a Docker container while running, and ensures it's deleted afterwards. """

    def __enter__(self):
        self.start()
        if not self.attrs['State']['Running']:
            print(f"Waiting for container with name: '{self.name}' to start.")
            sleep(15)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.stop()
            self.remove()
        except (NotFound, APIError):
            pass  # Container is most likely already deleted, happens when the container has auto_remove set to True.
