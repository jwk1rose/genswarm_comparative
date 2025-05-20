class TextParseError(Exception):
    pass


class CodeParseError(Exception):
    pass


class GrammarError(Exception):
    def __init__(self, message, grammar_error) -> None:
        super().__init__(message)
        self._grammar_error = grammar_error
