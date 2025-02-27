class WEBaseException(Exception):
    pass


class InvalidTextureFormat(WEBaseException):
    pass


class UnknownMagicError(WEBaseException):
    pass


class InvalidContainerVersion(WEBaseException):
    pass


class DecompressionError(WEBaseException):
    pass
