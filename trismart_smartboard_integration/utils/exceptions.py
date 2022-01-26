class SmartBoardError(Exception):
    """The base class for Trismart exceptions."""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)

class HTTPError(SmartBoardError):
    """An exception raised when an HTTP request returns with a bad code."""