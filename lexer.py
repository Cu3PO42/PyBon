"""
The Lexer for Python Bonsai.

Exports:
    Lexer: class - the Lexer itself; emits Tokens
    Token: class - the Tokens emitted by the Lexer
"""

def _wrap_Lexer() -> tuple:

    """
    Return the Lexer and Token classes.

    Wraps the Lexer class and various help classes and data structures
    as to only export the needed ones.

    @return: the classes to be exported, i.e. Lexer and Token
    @rtype: tuple
    """

    import re
    from collections import deque

    PB_RULES = [
        ("INDENT",              r"^[ ]+"),
        ("WHITESPACE",          r"[ ]+"),
        ("KEYWORD",             r"(?:if|label|goto)(?=[ ])|(?:else|halt)"),
        ("LABEL_IDENTIFIER",    r"\.[_a-zA-Z]?\w*"),
        ("IDENTIFIER",          r"[_a-zA-Z]\w*"),
        ("NUMBER",              r"\d+"),
        ("COMPARISON_OPERATOR", r">=?|<=?|==|!="),
        ("ASSIGNING_OPERATOR",  r"[-+]?="),
        ("ARITHMETIC_OPERATOR", r"[-+]"),
        ("COLON",               r":"),
        ("COMMENT",             r"#.*"),
        ("STRING",               "(?P<BEGIN>(?P<ML>[\"|']{3})|\"|')(?P<RES>(?(ML)(?:.|\\r?\\n)*?|.*?))(?P=BEGIN)"),
        ("SEMICOLON",           r";"),
        ("NEW_LINE",            r"\r?\n")
    ]
    """RegExp rules for the various tokens that can occur on Python Bonsai"""

    class LexerError(Exception):

        """Abstract class for all errors thrown by the Lexer."""

        pass

    class Token(object):

        """
        Token class that is emitted by the Lexer.

        Knows about its type and value and accurate position.

        Properties:
            typ       - the type of this token, e.g. IDENTIFIER, STRING, etc.
            val       - the exact substring that produced this token
            pos       - absolute position of the first character of this token
            line      - the line on which this token was found
            posInLine - position of the first character of this token relative
                        to the start of the line
        """

        def __init__(self, typ: str, value: str, pos: int, line: int, posInLine: int):
            """
            Initialize a Token with provided data.

            Squirrels all the passed data away and initializes the public properties.

            Arguments:
                @param typ:       the type of this token, e.g. IDENTIFIER, STRING, etc.
                @param value:     the exact substring that produced this token
                @param pos:       absolute position of the first character of this token
                @param line:      the line on which this token was found
                @param posInLine: position of the first character of this token relative
                                  to the start of the line

                @type typ: str
                @type value: str
                @type pos: int
                @type line: int
                @type posInLine: int
            """
            self.typ = typ
            """@type: str"""
            self.val = value
            """@type: str"""
            self.pos = pos
            """@type: int"""
            self.line = line
            """@type: int"""
            self.posInLine = posInLine
            """@type: int"""

        def __repr__(self) -> str:
            """
            @return: string representation of the Token
            @rtype: str
            """
            return "Token: {typ} ({val}) at line {line}, {pos}".format(
                typ=self.typ,
                val=repr(self.val),
                line=self.line+1,
                pos=self.posInLine+1
            )

        __str__ = __repr__

        def __bool__(self):
            return True

    class Lexer(object):

        """
        Lexer that tokenizes Python Bonsai and emits the found Tokens.

        Methods:
            token()    - return the next Token in the string
                         or None if the end of the string is reached;
                         raises a LexerError if the next substring does not match any rule
            tokens()   - returns a list of all token
            __iter__() - define an iterator over all tokens

        This class does not expose any public properties.

        Comments and insignificant whitespace will be ignored.
        New lines that are not followed by code will be ignored.
        Instead of emitting an INDENT token at the start of every indented line,
        the lexer will instead emit an INDENT token for each more indented line
        and emit an appropriate DEDENT token. Raises LexerError for an unmatched
        dedent.
        """

        def __init__(self, pyBonCode: str):
            """
            Create a Lexer for the given string.

            Arguments:
                @param pyBonCode: the Python Bonsai code to tokenize

                @type pyBonCode: str
            """
            self.regex = re.compile("|".join("(?P<G{GROUP_INDEX}>{RULE})".format(GROUP_INDEX=i, RULE=
                                    re.sub(r"\(\?P((<)|=)(.+?)((?(2)>.*?))\)",
                                           r"(?P\1G{GROUP_INDEX}_\3\4)".format(GROUP_INDEX=i), rule))
                                    for i, (typ, rule) in enumerate(PB_RULES)), re.MULTILINE)
            """@type: SRE_Pattern"""
            # join all RegExp into a single one by alternation
            # first prefix all group names by unique index to avoid naming conflicts
            self.types = dict(("G{}".format(i), typ) for i, (typ, rule) in enumerate(PB_RULES))
            """@type: dict"""
            # name all groups by index and store actual names in table, because group names
            # must be valid Python identifiers
            self.string = re.sub(r"^([\r?\n](#.*)?)*", "",
                                 re.sub(r"^([ ]*)(\t+)", lambda m: " "*8*(len(m.group(2))+len(m.group(1))//8),
                                        pyBonCode.replace("\f", "")))
            """@type: str"""
            # calculate actual indentation according to Python language reference
            # and remove leading comments and white lines
            self.pos = len(self.string)-len(pyBonCode)
            """@type: int"""
            self.line = pyBonCode.count("\n", 0, self.pos)
            """@type: int"""
            self.posInLine = 0
            """@type: int"""
            self.indent = [0]
            """@type: list"""
            self.queue = deque()
            """@type: deque"""

        def token(self) -> Token:
            """
            Return the next token.

            This method will change the Lexer object itself by storing
            the new position in the string.

            @return: the next token
            @rtype: Token
            """
            orgLine = self.line
            orgPosInLine = self.posInLine
            # emit queued tokens before getting new ones
            if self.queue:
                return self.queue.popleft()
            elif self.pos < len(self.string):
                match = self.regex.search(self.string, self.pos)
                if match and match.start() == self.pos:
                    self.pos = match.end()
                    typ = self.types[match.lastgroup]
                    if typ == "NEW_LINE":
                        self.line += 1
                        self.posInLine = 0
                        # check if the new line is followed by code and skip
                        # insignificant white lines
                        next_token_match = self.regex.search(self.string, self.pos)
                        if next_token_match:
                            next_token = self.types[next_token_match.lastgroup]
                            if next_token == "NEW_LINE":
                                return self.token()
                            elif next_token == "COMMENT":
                                self.pos = next_token_match.end()
                                return self.token()
                            elif next_token == "INDENT":
                                _2next_token_match = self.regex.search(self.string, next_token_match.end())
                                if _2next_token_match:
                                    _2next_token = self.types[_2next_token_match.lastgroup]
                                    if _2next_token == "NEW_LINE":
                                        self.pos = next_token_match.end()
                                        return self.token()
                                    elif _2next_token == "COMMENT":
                                        self.pos = _2next_token_match.end()
                                        return self.token()
                                else:
                                    return self.token()
                            else:
                                while self.indent[-1] > 0:
                                    self.indent.pop()
                                    self.queue.append(Token("DEDENT", "",
                                                            next_token_match.start(), self.line+1, 0))
                        else:
                            return self.token()
                    self.posInLine += match.end() - match.start()
                    if typ == "INDENT":
                        # compare to previous indent and emit indent
                        # or dedent token(s) if appropriate
                        indent = len(match.group())
                        if indent > self.indent[-1]:
                            self.indent.append(indent)
                            return Token("INDENT", match.group(), match.start(), self.line, self.posInLine)
                        elif indent == self.indent[-1]:
                            return self.token()
                        else:
                            while self.indent[-1] != indent:
                                self.indent.pop()
                                self.queue.append(Token("DEDENT", match.group(),
                                                        match.start(), self.line, self.posInLine))
                            if self.indent[-1] > indent:
                                raise LexerError("Unmatched dedent in line {}.".format(self.line))
                            return self.queue.popleft()
                    elif typ in ["COMMENT", "WHITESPACE"]:
                        # comments and whitespace are ignored
                        return self.token()
                    elif typ == "KEYWORD":
                        # if a keyword is found use the value as the token's type
                        return Token(match.group().upper(), match.group(), match.start(), orgLine, orgPosInLine)
                    else:
                        return Token(typ, match.groupdict().get(match.lastgroup+"_RES", match.group()),
                                     match.start(), orgLine, orgPosInLine)
                else:
                    # if the token matches now rule at all
                    raise LexerError("The symbol {} at line {}, {} does not match any rule.".format(
                                     self.string[self.pos], self.line, self.posInLine))
            elif self.pos == len(self.string):
                self.pos += 1
                self.line += 1
                while self.indent[-1]:
                    self.indent.pop()
                    self.queue.append(Token("DEDENT", "", self.pos, self.line, 0))
                self.queue.append(Token("EOF", "$", self.pos, self.line, 0))
                return Token("NEW_LINE", "\n", self.pos-1, self.line-1, self.posInLine)
                # at the end of the string, emit a final new line,
                # appropriate dedents and an end-of-file token
            else:
                # if the whole string was processed
                return None

        def tokens(self) -> list:
            """
            Return a list of all tokens.

            @return: a list of all tokens
            @rtype: list
            """
            return list(self)

        def __iter__(self):
            """
            Define an iterator for iterating over all tokens.

            @return: the iterator
            @rtype: generator
            """
            token = True
            while token:
                token = self.token()
                if token:
                    yield token

    return Lexer, Token

Lexer, Token = _wrap_Lexer()