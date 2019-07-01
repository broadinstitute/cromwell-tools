class Error(Exception):
    pass


class WorkflowFailedError(Error):
    pass


class WorkflowUnknownError(Error):
    pass
