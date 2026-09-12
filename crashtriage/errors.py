class TriageError(Exception):
    exit_code = 1


class ConfigError(TriageError):
    exit_code = 2


class InputError(TriageError):
    exit_code = 3