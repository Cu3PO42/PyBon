"""
Syntactic analyzer for Python Bonsai. The parser builds an abstract syntax tree.

Exports:
    AST: class                    - root of an abstract syntax tree
    ASTNode: class                - node of an abstract syntax tree
    PDA: class                    - a simple pushdown automaton
    InvalidTransitionError: class - an error that is raise by the PDA if no
                                    valid transition can be found
    SyntacticAnalysis: func       - parse Python Bonsai and return an ast
"""

class AST(object):

    """
    Root of an abstract syntax tree.

    The abstract syntax tree stores the original program in tree form
    with all insignificant information such as semicola removed.

    Also stores a symbol table and used registers.
    Provides convenient methods for construction.

    Properties:
        root        - root node of the tree
        symbolTable - a table containing all used labels and registers
        registers   - the constant values for registers

    Methods:
        addBlock(type: str, value: str)/ - add a new child node and enter it
        addBlock(node: ASTNode)
        leaveBlock()                     - go to the parent node
        addNode(type: str, value: str)/  - add a new child node, but do not leave the parent
        addNode(node: ASTNode)
    """

    def __init__(self):
        self.root = ASTNode(None, "BLOCK")
        """@type: ASTNode"""
        self.currentNode = self.root
        """@type: ASTNode"""
        self.symbolTable = {}
        """@type: dict"""
        self.registers = []
        """@type: list"""

    def addBlock(self, *args):
        """
        AST.addBlock(type: str, value: str)
        AST.addBlock(node: ASTNode)

        Add a new child node and enter it.
        """
        self.currentNode = self.currentNode.addChild(*args)

    def leaveBlock(self):
        """Go to the parent node."""
        self.currentNode = self.currentNode.parent

    def addNode(self, *args):
        """
        AST.addNode(type: str, value: str)
        AST.addNode(node: ASTNode)

        Add a new child node, but do not leave the parent.
        """
        self.currentNode.addChild(*args)

class ASTNode(object):

    """
    Node of an abstract syntax tree.

    Stores its own type and value, as well as its parent, its children and
    decorators that may be added by semantic analysis.

    Properties:
        typ        - the type of this node, e.g. BRANCH, ASSIGNMENT, etc.
        val        - the substring that produced this node
        children   - an ordered list of all children of this node
        parent     - a reference to the immediate predecessor of this node
        decorators - a list of all decorators added by semantic analysis

    Methods:
        addChild(type: str, value: str)/ - adds a new child to this node
        addChild(node: ASTNode)
    """

    def __init__(self, parent, typ: str, val=""):
        """
        Initialize node with given values.

        Parameters:
            @param parent: a reference to the immediate predecessor of this node
            @param typ:    the type of this node, e.g. BRANCH, ASSIGNMENT, etc.
            @param val:    the substring that produced this node

            @type parent: ASTNode
            @type typ:    str
            @type val:    str
        """
        self.parent = parent
        """@type: ASTNode"""
        self.typ = typ
        """@type: str"""
        self.val = val
        """@type: str"""
        self.children = []
        """@type: list"""
        self.decorators = []
        """@type: list"""

    def addChild(self, *args):
        """
        ASTNode.addChild(type: str, value: str)
        ASTNode.addChild(node: ASTNode)

        Adds either a given node as a new child or creates a new one
        with given parameters.
        """
        if type(args[0]) == ASTNode:
            self.children.append(args[0])
            args[0].parent = self
        else:
            self.children.append(ASTNode(self, *args))
        return self.children[-1]

class PDA(object):

    """
    A simple pushdown automaton used for parsing.

    Consumes a stream of tokens and processes them using given transitions.
    May raise InvalidTransitionError in case the tokens do not form a word of
    the language specified using the transition rulesl

    Properties:
        ast - the abstract syntax tree built by the parser
    """

    def __init__(self, tokens: list, initial_state: str, transitions: dict, accepted_states: list, initial_stack=[]):
        """
        Initialize a pushdown automaton with processing data.

        Parameters:
            @param tokens:          a list of tokens to process
            @param initial_state:   the state at which to start processing
            @param transitions:     a dict of all defined transitions from one state to another
                                    the transitions have the format:
                                        (current_state, symbol, top_of_stack) ->
                                            (new_state, list_of_additional_actions)
                                        Where either symbol or top_of_stack can be None, indicating
                                        that the value in question is irrelevant and
                                        list_of_additional_actions is a list of functions with the
                                        signature fn(pda, token, *args).
                                        It will always be looked for a rule that matches all three keys,
                                        then for one with the input symbol being insignificant
                                        and lastly for one with the top of the stack being insignificant.
                                        In case no rule matching the current state is found,
                                        InvalidTransitionError is used.
            @param accepted_states: a list of all accepted states; should the stream end when the current
                                    state is one of these, the input word is a word of the specified language
            @param initial_stack:   a list of symbols that should be pushed on the stack before the actual
                                    processing starts

            @type tokens:          list
            @type initial_state:   str
            @type transitions:     dict
            @type accepted_states: list
            @type initial_stack:   list
        """
        self.tokens = tokens
        """@type: list"""
        self.head = 0
        """@type: int"""
        self.current_state = initial_state
        """@type: str"""
        self.transitions = transitions
        """@type: dict"""
        self.accepted_states = accepted_states
        """@type: list"""
        self.stack = ["#"]
        """@type: list"""
        self.stack.extend(initial_stack)
        self.ast = AST()
        """@type: AST"""
        self.process()

    def process(self):
        """Do the actual processing of the given tokens."""
        while self.head < len(self.tokens):
            token = self.tokens[self.head]
            self.head += 1
            next_state = self.transitions.get((self.current_state, token.typ, self.stack[-1]),
                         self.transitions.get((self.current_state, None, self.stack[-1]),
                         self.transitions.get((self.current_state, token.typ, None))))
            # get the next state following the rules described in __init__'s docstring
            if next_state is not None:
                self.current_state = next_state[0]
                for fn in next_state[1]:
                    fn[0](self, token, *fn[1:])
                # do all the additional processing
            else:
                raise InvalidTransitionError("{value} may not be used in state {state} with top of stack being {stack}.".format(value=token.typ, state=self.current_state, stack=self.stack[-1]))
        return self.current_state in self.accepted_states

class InvalidTransitionError(Exception):

    """Abstract class for errors occurring during parsing."""

    pass

def _wrap_PB_STATES() -> dict:

    """
    Wrap the transition rules as not to expose the "additional action" functions.

    @return: the transition rules for parsing Python Bonsai
    @rtype: dict
    """

    def push(self, token, e):
        self.stack.append(e)

    def pushToken(self, token):
        self.stack.append(token.val)

    def pop(self, token):
        self.stack.pop()

    def repeat(self, token):
        self.head -= 1

    def addBlock(self, token, typ, val=None):
        self.ast.addBlock(typ, (val if val is not None else token.val))

    def addNode(self, token, typ, val=None):
        self.ast.addNode(typ, (val if val is not None else token.val))

    def leaveBlock(self, token):
        self.ast.leaveBlock()

    def rewrite(self, token, typ):
        self.ast.currentNode.typ = typ
        self.ast.currentNode.val = token.val

    return {
        # GENERAL SEQUENCE STUFF
        ("SEQUENCE", "NEW_LINE", None): ("SEQUENCE", [(push, "^")]),
        ("EOL", "NEW_LINE", "^"): ("SEQUENCE", []),
        ("EOL", "NEW_LINE", None): ("SEQUENCE", [(push, "^")]),
        ("EOL", "SEMICOLON", "^"): ("SEQUENCE", [(pop, )]),
        ("EOL", "SEMICOLON", None): ("SEQUENCE", []),

        # DOCSTRING
        ("SEQUENCE", "STRING", None): ("EOL", [(addNode, "DOCSTRING")]),

        # LABEL/GOTO
        ("SEQUENCE", "LABEL", None): ("LABEL", [(addBlock, "LABEL")]),
        ("SEQUENCE", "GOTO", None): ("LABEL", [(addBlock, "GOTO")]),
        ("LABEL", "LABEL_IDENTIFIER", None): ("EOL", [(addNode, "LABEL_ID"), (leaveBlock, )]),

        # HALT
        ("SEQUENCE", "HALT", None): ("EOL", [(addNode, "HALT")]),

        # ARITHMETIC EXPRESSION
        ("ARITHMETIC_EXPRESSION", "NUMBER", None): ("ARITHMETIC_EXPRESSION_COMPLETE", [(addNode, "CONSTANT")]),
        ("ARITHMETIC_EXPRESSION", "IDENTIFIER", None): ("ARITHMETIC_EXPRESSION_COMPLETE", [(addNode, "REGISTER")]),
        ("ARITHMETIC_EXPRESSION", None, "+"): ("ARITHMETIC_EXPRESSION", [(pop, ), (repeat, )]),
        ("ARITHMETIC_EXPRESSION", None, "-"): ("ARITHMETIC_EXPRESSION_SIGN_NEGATIVE", [(pop, ), (repeat, )]),
        ("ARITHMETIC_EXPRESSION", "ARITHMETIC_OPERATOR", None): ("ARITHMETIC_EXPRESSION", [(pushToken, )]),
        ("ARITHMETIC_EXPRESSION_SIGN_NEGATIVE", "NUMBER", None): ("ARITHMETIC_EXPRESSION_COMPLETE", [(addBlock, "SIGN", "-"), (addNode, "CONSTANT"), (leaveBlock, )]),
        ("ARITHMETIC_EXPRESSION_SIGN_NEGATIVE", "IDENTIFIER", None): ("ARITHMETIC_EXPRESSION_COMPLETE", [(addBlock, "SIGN", "-"), (addNode, "REGISTER"), (leaveBlock, )]),
        ("ARITHMETIC_EXPRESSION_SIGN_NEGATIVE", None, "+"): ("ARITHMETIC_EXPRESSION_SIGN_NEGATIVE", [(pop, ), (repeat, )]),
        ("ARITHMETIC_EXPRESSION_SIGN_NEGATIVE", None, "-"): ("ARITHMETIC_EXPRESSION", [(pop, ), (repeat, )]),
        ("ARITHMETIC_EXPRESSION_SIGN_NEGATIVE", "ARITHMETIC_OPERATOR", None): ("ARITHMETIC_EXPRESSION_SIGN_NEGATIVE", [(pushToken, )]),
        ("ARITHMETIC_EXPRESSION_COMPLETE", "ARITHMETIC_OPERATOR", None): ("ARITHMETIC_EXPRESSION", [(pushToken, )]),

        # ASSIGNMENT
        ("SEQUENCE", "IDENTIFIER", None): ("ASSIGNMENT", [(addBlock, "ASSIGNMENT"), (addNode, "REGISTER")]),
        ("ASSIGNMENT", "ASSIGNING_OPERATOR", None): ("ARITHMETIC_EXPRESSION", [(push, "ASSIGNMENT"), (rewrite, "ASSIGNMENT"), (addBlock, "ARITHMETIC_OPERATOR", "+")]),
        ("ARITHMETIC_EXPRESSION_COMPLETE", "NEW_LINE", "ASSIGNMENT"): ("EOL", [(pop, ), (repeat, ), (leaveBlock, ), (leaveBlock, )]),
        ("ARITHMETIC_EXPRESSION_COMPLETE", "SEMICOLON", "ASSIGNMENT"): ("EOL", [(pop, ), (repeat, ), (leaveBlock, ), (leaveBlock, )]),

        # BLOCK STATEMENT
        ("SEQUENCE", None, "EXPECT_BLOCK"): ("SEQUENCE", [(pop, ), (push, "EXPECT_BLOCK_1"), (repeat, ), (addBlock, "BLOCK")]),
        ("SEQUENCE", "NEW_LINE", "EXPECT_BLOCK_1"): ("SEQUENCE", [(pop, ), (push, "EXPECT_INDENT")]),
        ("SEQUENCE", "INDENT", "EXPECT_INDENT"): ("SEQUENCE", [(pop, ), (push, "INDENT"), (push, "^")]),
        ("SEQUENCE", "DEDENT", "^"): ("SEQUENCE", [(pop, ), (repeat, )]),
        ("SEQUENCE", "DEDENT", "INDENT"): ("SEQUENCE", [(pop, ), (leaveBlock, )]),
        ("SEQUENCE", "NEW_LINE", "LINE_BLOCK"): ("SEQUENCE", [(pop, ), (leaveBlock, )]),
        ("EOL", "NEW_LINE", "EXPECT_BLOCK_1"): ("SEQUENCE", [(pop, ), (leaveBlock, )]),
        ("EOL", "NEW_LINE", "LINE_BLOCK"): ("SEQUENCE", [(pop, ), (leaveBlock, )]),
        ("EOL", "SEMICOLON", "EXPECT_BLOCK"): ("SEQUENCE", [(pop, ), (push, "LINE_BLOCK")]),

        # CONDITIONS
        ("ARITHMETIC_EXPRESSION_COMPLETE", "COMPARISON_OPERATOR", "COMPOUND_0"): ("ARITHMETIC_EXPRESSION", [(pop, ), (push, "COMPOUND_1"), (leaveBlock, ), (rewrite, "COMPARISON"), (addBlock, "ARITHMETIC_OPERATOR", "+")]),
        ("ARITHMETIC_EXPRESSION_COMPLETE", "COLON", "COMPOUND_0"): ("SEQUENCE", [(pop, ), (push, "EXPECT_BLOCK"), (leaveBlock, ), (addNode, "CONSTANT", "0"), (leaveBlock, )]),
        ("ARITHMETIC_EXPRESSION_COMPLETE", "COLON", "COMPOUND_1"): ("SEQUENCE", [(pop, ), (push, "EXPECT_BLOCK"), (leaveBlock, ), (leaveBlock, )]),

        # IF STATEMENT
        ("SEQUENCE", "IF", "^"): ("ARITHMETIC_EXPRESSION", [(pop, ), (push, "IF"), (push, "COMPOUND_0"), (addBlock, "BRANCH"), (addBlock, "COMPARISON", ">"), (addBlock, "ARITHMETIC_OPERATOR", "+")]),
        ("SEQUENCE", "ELSE", "IF"): ("ELSE", [(pop, ), (push, "END_BLOCK")]),
        ("ELSE", "COLON", None): ("SEQUENCE", [(push, "EXPECT_BLOCK")]),
        ("SEQUENCE", None, "END_BLOCK"): ("SEQUENCE", [(pop, ), (repeat, ), (leaveBlock, )]),
        ("SEQUENCE", None, "IF"): ("SEQUENCE", [(pop, ), (repeat, ), (addNode, "BLOCK"), (leaveBlock, )]),

        # END OF FILE
        ("SEQUENCE", "EOF", "^"): ("SEQUENCE", [(pop, ), (repeat, )]),
        ("SEQUENCE", "EOF", "#"): ("EOF", [])
    }

def SyntacticAnalysis(tokens: list) -> AST:
    """
    Parse the given tokens and return an abstract syntax tree.

    Parameters:
        @param tokens: the list of tokens to be parsed

        @type tokens: list

    @return: the abstract syntax tree representing the input stream
    @rtype: AST
    """
    return PDA(tokens, "SEQUENCE", _wrap_PB_STATES(), ["EOF"], ["^"]).ast