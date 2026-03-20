from rclpy.node import Node

from .did import load_did


class DIDNode(Node):
    def __init__(self, node_name: str, did_retry_sec: float = 2.0):
        super().__init__(node_name)

        self.did = None
        self.did_timer = self.create_timer(did_retry_sec, self.try_load_did)

    def try_load_did(self):
        if self.did is not None:
            if self.did_timer is not None:
                self.did_timer.cancel()
            return

        did = load_did()
        if did is not None:
            self.did = did
            self.get_logger().info(f"DID loaded: {self.did}")

            if self.did_timer is not None:
                self.did_timer.cancel()

            self.on_did_loaded()

    def on_did_loaded(self):
        """
        Optional hook for child classes.
        Override this in subclasses if needed.
        """
        pass

    def has_did(self):
        return self.did is not None