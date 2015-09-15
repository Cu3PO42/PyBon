"""
Semantic Analyzer for Python Bonsai. It decorates a given AST with context-based information.

Exports:
    SematicAnalysis(func) - perform the semantic analysis and return the decorated ast
"""

from syntactic_analyzer import ASTNode

def SemanticAnalysis(syntaxTree):

    """
    Perform the semantic analysis and return the decorated ast.

    Please note that this will modify the passed syntaxTree.

    Parameters:
        @param syntaxTree: the ast to be analyzed and decorated

        @type syntaxTree: AST

    @return: the decorated syntax tree
    @rtype: AST
    """

    class SemanticError(Exception):

        """Abstract class for all errors thrown by the SemanticAnalysis."""

        pass

    class Analyzer(object):

        """
        Class that performs the actual analysis on construction.

        This class does not expose any public methods or properties
        """

        def __init__(self):
            self.hasBranched = False
            """@type: bool"""
            self.analyzeNode(syntaxTree.root)

        def analyzeNode(self, node: ASTNode):
            """
            Analyze the given node and traverse the tree using recursion.

            Raises SemanticError in case previously undefined symbols are used, etc. or
            if a variable is assigned a constant negative value.

            Parameter:
                @param node: the node to analyze

                @type node: ASTNode
            """
            if node.typ in ["BRANCH", "LABEL"]:
                self.hasBranched = True
                # all assignments are now dynamic
                for child in node.children:
                    self.analyzeNode(child)
            elif node.typ == "ASSIGNMENT":
                self.analyzeNode(node.children[1])
                # check if the right side contains any undefined identifiers
                if not self.hasBranched and node.children[0].val not in syntaxTree.symbolTable:
                    # this is the first assignment of a variable before the program has branched
                    self.checkSum(node.children[1])
                    # optimize constant expressions
                    if node.val != "=":
                        self.analyzeNode(node.children[0])
                        # the left side must also be defined for augmented assignments
                        # which it is not -> raises SemanticError
                        # is is not directly raised to avoid code duplication
                    if node.children[1].typ == "CONSTANT":
                        node.decorators.append("STATIC_ASSIGNMENT")
                        syntaxTree.symbolTable[node.children[0].val] = len(syntaxTree.registers)
                        syntaxTree.registers.append(node.children[1].val)
                        # can be translated to the constant start value of a register
                    else:
                        node.decorators.append("DYNAMIC_ASSIGNMENT")
                        syntaxTree.symbolTable[node.children[0].val] = len(syntaxTree.registers)
                        syntaxTree.registers.append(0)
                        # even though it is the first assignment it is a mathematical expression and must be calculated
                else:
                    self.analyzeNode(node.children[0])
                    # variable must be declared at the beginning of the file with a constant assignment
                    if node.val == "=":
                        if node.children[1].val == "+":
                            # right side is a sum of statements
                            for i, child in enumerate(node.children[1].children):
                                if child.val == node.children[0].val:
                                    node.children[1].children.pop(i)
                                    node.val = "+="
                                    node.decorators.append("AUGMENTED_ASSIGNMENT")
                                    self.checkSum(node.children[1], False)
                                    # optimize constant expressions
                                    break
                                    # an assignment may be more accurately represented by an augmented assignment
                                    # if the variable is used on the right side as well to simplify translation process
                            else:
                                node.decorators.append("DYNAMIC_ASSIGNMENT")
                                self.checkSum(node.children[1])
                                # optimize constant expressions
                        else:
                            # right side is either a constant or a register
                            node.decorators.append("DYNAMIC_ASSIGNMENT")
                            self.checkSum(node.children[1])
                            # optimize constant expressions
                    else:
                        self.checkSum(node.children[1], False)
                        # optimize constant expressions
                        node.decorators.append("AUGMENTED_ASSIGNMENT")
            elif node.typ == "IDENTIFIER" and node.val not in syntaxTree.symbolTable:
                # undefined identifier is used
                raise NameError("{} has not been declared before.".format(node.val))
            elif node.typ == "SIGN" and node.parent.val not in ["+", "+=", "-="]:
                raise SemanticError("Constant values must never be smaller than 0.")
            elif node.typ == "COMPARISON":
                for child in node.children:
                    self.checkSum(child)
                    # optimize constant expressions
                    self.analyzeNode(child)
            else:
                # no special check or decorators required
                # simply traverse tree
                for child in node.children:
                    self.analyzeNode(child)

        def checkSum(self, node: ASTNode, assertPositive=True):
            """
            Optimize sums and optionally assert that there is no negative constant.

            Condense the constant addends before a register is found and
            optionally assert they are not negative.
            If the sum only consists of only a single addend, move it one level up
            and remove the sum.

            Parameters:
                @param node:           the node to check
                @param assertPositive: if True raise an error if a negative
                                       constant is calculated before the first
                                       register occurs

                @type node:           ASTNode
                @type assertPositive: bool
            """
            constant = 0
            indices = []
            for i, child in enumerate(node.children):
                if child.typ == "CONSTANT":
                    constant += int(child.val)
                    indices.append(i)
                elif child.typ == "SIGN" and child.children[0].typ == "CONSTANT":
                    constant -= int(child.children[0].val)
                    indices.append(i)
                # find all constant and sum them up
            for i in reversed(indices):
                node.children.pop(i)
                # remove the constant from the children
            if constant > 0:
                node.children.insert(0, ASTNode(node, "CONSTANT", str(constant)))
                # a positive constant should be added first
            elif constant < 0:
                if assertPositive:
                    for child in node.children:
                        if child.typ != "SIGN":
                            break
                    else:
                        raise SemanticError("Constant values must never be smaller than 0.")
                        # if there are only negative addends an ZeroDecrementError will occur
                node.addChild("SIGN", "-")
                node.children[-1].addChild("CONSTANT", str(-constant))
                # a negative constant is added last
                # a new sign is therefore inserted
            if len(node.children) == 1:
                node.typ = node.children[0].typ
                node.val = node.children[0].val
                node.children = node.children[0].children
                # remove the sum and only use register or constant if possible


    Analyzer()
    # do the semantic analysis
    return syntaxTree