class UnknownOpCodeException(Exception):
    """
    A class to raise unknown op code exceptions.
    """
    def __init__(self, op_code):
        Exception.__init__(self, "Unknown op-code: {:X}".format(op_code))