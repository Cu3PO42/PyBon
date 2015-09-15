"""
Intermediate code for Python Bonsai.

The intermediate code con be constructed from abstract syntax tree generated
by the parser and decorated by the semantic analysis and be compiled to
actual Bonsai code.
It is also the representation of the code on which optimizations are applied.

Exports:
    IntermediateCode: class - assembly-like representation of the code
    Instruction: class      - a single instruction used in the intermediate code
    Operand: class          - a single operand for an instruction
"""

from collections import namedtuple
from itertools import chain

class IntermediateCode(object):

    """
    Intermediate Code for Python Bonsai.

    Stores a list of instructions, the registers, docstrings and a symbol table.
    All data structures are empty upon initialization. Call one of the instances'
    methods to fill them with data, such as fromSyntaxTree(ast).

    Properties:
        instructions - a list of Instructions
        symbolTable  - a table resolving all used identifiers
        registers    - a list containing the start values for manually set registers
        comments     - a list containing all the used docstrings

    Methods:
        fromSyntaxTree(ast) - fills the data structures with the data provided
                              in the ast and compiles Python Bonsai to the
                              intermediate code
        compile()           - compile the intermediate code and return the
                              equivalent Bonsai code
    """

    def __init__(self):
        self.instructions = []
        """@type: list"""
        self.symbolTable = {}
        """@type: dict"""
        self.registers = []
        """@type: list"""
        self.comments = []
        """@type: list"""
        self.helpRegisterScopes = {}
        """@type: dict"""
        self.helpRegisterCount = 0
        """@type: int"""
        self.ifCount = 0
        """@type: int"""

    def fromSyntaxTree(self, syntaxTree):

        """
        Compile Python Bonsai code stored in an abstract syntax tree.

        Fills the internal data structures with the values obtained from the tree.
        Contains several helper functions that needn't be exposed.

        Parameters:
            @param syntaxTree: the abstract syntax tree to be compiled

            @type syntaxTree: AST
        """

        def calculateArithmeticExpression(node, baseOperand: Operand, mode=("add", "sub")):
            """
            Add/substract the arithmetic expression in node to/from baseOperand.

            Parameters:
                @param node:        an arithmetic expression node, either a constant,
                                    a register or a sum
                @param baseOperand: the register to add the values to
                @param mode:        define whether positive/negative values should be
                                    added/subtracted; useful for negative augmented
                                    assignments

                @type node:        ASTNode
                @type baseOperand: Operand
                @type mode:        tuple
            """
            if node.typ in ["CONSTANT", "REGISTER"]:
                self.instructions.append(Instruction(mode[0], baseOperand, Operand(node.typ, node.val)))
            else:
                for child in node.children:
                    if child.val == "-":
                        self.instructions.append(Instruction(mode[1], baseOperand, Operand(child.children[0].typ, child.children[0].val)))
                    else:
                        self.instructions.append(Instruction(mode[0], baseOperand, Operand(child.typ, child.val)))

        def getArithmeticOperand(node) -> Operand:
            """
            Return an operand for the given arithmetic expression.

            This can be either a constant, a register or a help register
            containing the result of a more complicated expression.
            In case a help register is returned, please remember to set
            it to zero once it is no longer needed.

            Parameters:
                @param node: the arithmetic expression to handle

                @type node: ASTNode

            @return: the operand for the given arithmetic expression
            @rtype: Operand
            """
            if node.typ in ["CONSTANT", "REGISTER"]:
                return Operand(node.typ, node.val)
            else:
                helpRegister = Operand("HELP_REGISTER", self.helpRegisterCount)
                self.helpRegisterCount += 1
                calculateArithmeticExpression(node, helpRegister)
                return helpRegister

        def traverseTree(node):
            """
            Traverse the syntax tree using recursion and compile the nodes.

            Parameters:
                @param node: the current node which to compile and traverse

                @type node: ASTNode
            """
            if node.typ == "BLOCK":
                for child in node.children:
                    traverseTree(child)
            elif node.typ == "LABEL":
                self.symbolTable[node.children[0].val] = len(self.instructions)
            elif node.typ == "GOTO":
                self.instructions.append(Instruction("jmp", Operand("LABEL_IDENTIFIER", node.children[0].val), None))
            elif node.typ == "HALT":
                self.instructions.append(Instruction("hlt", None, None))
            elif node.typ == "ASSIGNMENT" and "DYNAMIC_ASSIGNMENT" in node.decorators:
                op = getArithmeticOperand(node.children[1])
                self.instructions.append(Instruction("mov", Operand("REGISTER", node.children[0].val), op))
                if op.typ == "HELP_REGISTER":
                    self.instructions.append(Instruction("mov", op, Operand("CONSTANT", "0")))
                    self.helpRegisterScopes[op.val] = len(self.instructions)
                # help registers must be reset after using them so they can be reused
            elif node.typ == "ASSIGNMENT" and "AUGMENTED_ASSIGNMENT" in node.decorators:
                calculateArithmeticExpression(node.children[1], Operand("REGISTER", node.children[0].val), {"+=": ("add", "sub"), "-=": ("sub", "add")}[node.val])
            elif node.typ == "DOCSTRING":
                self.comments.append(node.val.replace("\r\n", "\n").replace("\n", ";"))
            elif node.typ == "BRANCH":
                # a branch is compiled as:
                #        cmp op1, op2
                #        ji .IF
                #        (else instructions)
                #        ...
                #        jmp .ENDIF
                #    .IF (if instructions)
                #        ...
                # .ENDIF (next instructions)
                #
                # where op1, op2 can be registers or constants
                # please note that constants are moved into help registers first
                # ji being jg, jge, jl, jle, je or jne depending on the condition
                ifCount = self.ifCount
                self.ifCount += 1
                op1 = getArithmeticOperand(node.children[0].children[0])
                op2 = getArithmeticOperand(node.children[0].children[1])
                self.instructions.append(Instruction("cmp", op1, op2))
                self.instructions.append(Instruction({">": "jg", ">=": "jge", "<": "jl", "<=": "jle", "==": "je", "!=": "jne"}[node.children[0].val], Operand("LABEL_IDENTIFIER", ".IF_{}".format(ifCount)), None))
                traverseTree(node.children[2])
                self.instructions.append(Instruction("jmp", Operand("LABEL_IDENTIFIER", ".ENDIF_{}".format(ifCount)), None))
                self.symbolTable[".IF_{}".format(ifCount)] = len(self.instructions)
                traverseTree(node.children[1])
                self.symbolTable[".ENDIF_{}".format(ifCount)] = len(self.instructions)
                if op1.typ == "HELP_REGISTER":
                    self.instructions.append(Instruction("mov", op1, Operand("CONSTANT", "0")))
                    self.helpRegisterScopes[op1.val] = len(self.instructions)
                if op2.typ == "HELP_REGISTER":
                    self.instructions.append(Instruction("mov", op2, Operand("CONSTANT", "0")))
                    self.helpRegisterScopes[op2.val] = len(self.instructions)
                # help registers must be reset after using them so they can be reused

        self.symbolTable = syntaxTree.symbolTable
        self.registers = syntaxTree.registers
        # start with the symbol table and the registers from the ast
        traverseTree(syntaxTree.root)
        self.instructions.append(Instruction("hlt", None, None))
        # a 'hlt' is needed at the end of file to end the execution

    def compile(self) -> str:

        """
        Compile the intermediate code and return the Bonsai code.

        Contains helper functions for every intermediate instruction, that
        compile them to a series of equivalent Bonsai instructions.
        First compiles every instruction one after another and translates
        the intermediate code lines into Bonsai lines, e.g. for labels.
        It then replaces labels and relative addressing by absolute addresses
        and proceeds to substitute help registers by actual registers.
        A list of free help registers is always kept so that they can be reused
        in order to keep the number of help registers minimal.

        @return: actual Bonsai code
        @rtype: str
        """

        storage = type("Storage", (object, ), {
            "helpRegisterCount": self.helpRegisterCount,
            "head": 0
        })()
        bonInstructions = []
        helpRegisterScopes = {}

        # helper functions for compiling single instructions
        def compile_add(op1, op2):
            if op2.typ == "CONSTANT":
                bonInstructions.extend([("INC", op1.val)]*int(op2.val))
                # adding n is done by n INC instructions
            elif op2.typ in ["REGISTER", "HELP_REGISTER"]:
                op1 = op1.val
                op2 = op2.val
                bonInstructions.extend([
                    ("TST", op2),
                    ("JMP", "@+8"),
                    ("TST", storage.helpRegisterCount),
                    ("JMP", "@+2"),
                    ("JMP", "@+8"),
                    ("DEC", storage.helpRegisterCount),
                    ("INC", op1),
                    ("INC", op2),
                    ("JMP", "@-6"),
                    ("DEC", op2),
                    ("INC", storage.helpRegisterCount),
                    ("JMP", "@-11"),
                ])
                # works by first moving the register to be added into a help register
                # and moving it back to the source and adding it to the destination
                helpRegisterScopes[storage.helpRegisterCount] = len(bonInstructions)
                storage.helpRegisterCount += 1

        def compile_sub(op1, op2):
            if op2.typ == "CONSTANT":
                bonInstructions.extend([("DEC", op1.val)]*int(op2.val))
                # subtracting n is done by n DEC instructions
            elif op2.typ in ["REGISTER", "HELP_REGISTER"]:
                op1 = op1.val
                op2 = op2.val
                bonInstructions.extend([
                    ("TST", op2),
                    ("JMP", "@+8"),
                    ("TST", storage.helpRegisterCount),
                    ("JMP", "@+2"),
                    ("JMP", "@+8"),
                    ("DEC", storage.helpRegisterCount),
                    ("DEC", op1),
                    ("INC", op2),
                    ("JMP", "@-6"),
                    ("DEC", op2),
                    ("INC", storage.helpRegisterCount),
                    ("JMP", "@-11"),
                ])
                # works by first moving the register to be subtracted into a help register
                # and moving it back to the source and subtracting it from the destination
                helpRegisterScopes[storage.helpRegisterCount] = len(bonInstructions)
                storage.helpRegisterCount += 1

        def compile_mov(op1, op2):
            if op2.typ == "CONSTANT":
                bonInstructions.extend([
                    ("TST", op1.val),
                    ("JMP", "@+2"),
                    ("JMP", "@+3"),
                    ("DEC", op1.val),
                    ("JMP", "@-4")
                ])
                compile_add(op1, op2)
                # moving a constant works by setting the register to 0
                # and adding the constant
            elif op2.typ in ["REGISTER", "HELP_REGISTER"]:
                compile_mov(op1, Operand("CONSTANT", "0"))
                # the register is set to 0
                compile_add(op1, op2)
                # and the register added

        def compile_hlt(op1, op2):
            bonInstructions.append(("HLT", None))

        def compile_jmp(op1, op2):
            bonInstructions.append(("JMP", op1.val))

        def compile_cmp(op1, op2):
            storage.head += 1
            # this function also consumes the following jmp instruction
            # to determine what kind of condition needs to be checked
            branch = self.instructions[storage.head]
            if op2.val == "0":
                # any comparison with 0 is fast
                if branch.opcode in ["jg", "jne"]:
                    bonInstructions.extend([
                        ("TST", op1.val),
                        ("JMP", branch.op1.val)
                    ])
                elif branch.opcode == "jge":
                    bonInstructions.extend([
                        ("JMP", branch.op1.val)
                    ])
                elif branch.opcode == "jl":
                    raise CompilerError("Register can never be smaller than 0.")
                elif branch.opcode in ["jle", "je"]:
                    bonInstructions.extend([
                        ("TST", op1.val),
                        ("JMP", "@+2"),
                        ("JMP", branch.op1.val)
                    ])
            else:
                # these are the relative position of the true and false
                # branches from the various possible jump points
                # whether true or false is chosen during compilation
                # depends on the kind of condition
                LABEL1_TRUE = 9; LABEL1_FALSE = 14
                LABEL2_TRUE = 8; LABEL2_FALSE = 13
                LABEL3_TRUE = 5; LABEL3_FALSE = 10
                LABEL_RESTORE_BACK = 4
                LABEL_ELSE = 3
                register_sequence = []
                # will contain a list of instructions to increment the registers
                if op1.typ == "CONSTANT":
                    hr = storage.helpRegisterCount
                    storage.helpRegisterCount += 1
                    compile_add(Operand("HELP_REGISTER", hr), op1)
                    op1 = hr
                else:
                    op1 = op1.val
                    register_sequence.append(("INC", op1))
                if op2.typ == "CONSTANT":
                    hr = storage.helpRegisterCount
                    storage.helpRegisterCount += 1
                    compile_add(Operand("HELP_REGISTER", hr), op2)
                    op2 = hr
                else:
                    op2 = op2.val
                    register_sequence.append(("INC", op2))
                # constants are moved into help registers before the actual comparison
                # as this may cause code bloat please avoid that as much as possible
                LABEL1_TRUE = "@+{}".format(LABEL1_TRUE)
                LABEL2_TRUE = "@+{}".format(LABEL2_TRUE)
                LABEL3_TRUE = "@+{}".format(LABEL3_TRUE)
                LABEL1_FALSE = "@+{}".format(LABEL1_FALSE+len(register_sequence))
                LABEL2_FALSE = "@+{}".format(LABEL2_FALSE+len(register_sequence))
                LABEL3_FALSE = "@+{}".format(LABEL3_FALSE+len(register_sequence))
                LABEL_RESTORE_BACK = "@-{}".format(LABEL_RESTORE_BACK+len(register_sequence))
                LABEL_ELSE = "@+{}".format(LABEL_ELSE+len(register_sequence))
                # depending on how many help registers are needed the places to jump vary
                LABEL1, LABEL2, LABEL3 = {
                    "je": (LABEL1_FALSE, LABEL2_TRUE, LABEL3_FALSE),
                    "jne": (LABEL1_TRUE, LABEL2_FALSE, LABEL3_TRUE),
                    "jg": (LABEL1_FALSE, LABEL2_FALSE, LABEL3_TRUE),
                    "jge": (LABEL1_FALSE, LABEL2_TRUE, LABEL3_TRUE),
                    "jl": (LABEL1_TRUE, LABEL2_FALSE, LABEL3_FALSE),
                    "jle": (LABEL1_TRUE, LABEL2_TRUE, LABEL3_FALSE)
                }[branch.opcode]
                # this is a jump table for the various possible conditions
                bonInstructions.extend([
                    ("TST", op1),
                    ("JMP", "@+4"),
                    ("TST", op2),
                    ("JMP", LABEL1),
                    ("JMP", LABEL2),
                    ("TST", op2),
                    ("JMP", "@+2"),
                    ("JMP", LABEL3),
                    ("DEC", op1),
                    ("DEC", op2),
                    ("INC", storage.helpRegisterCount),
                    ("JMP", "@-11"),
                    ("TST", storage.helpRegisterCount),
                    ("JMP", "@+2"),
                    ("JMP", branch.op1.val),
                    ("DEC", storage.helpRegisterCount)] +
                    register_sequence + [
                    ("JMP", LABEL_RESTORE_BACK),
                    ("TST", storage.helpRegisterCount),
                    ("JMP", "@+2"),
                    ("JMP", LABEL_ELSE),
                    ("DEC", storage.helpRegisterCount)] +
                    register_sequence + [
                    ("JMP", LABEL_RESTORE_BACK)
                ])
                helpRegisterScopes[storage.helpRegisterCount] = len(bonInstructions)
                storage.helpRegisterCount += 1
                if type(op1) == int:
                    compile_mov(Operand("HELP_REGISTER", op1), Operand("CONSTANT", "0"))
                    helpRegisterScopes[op1] = len(bonInstructions)
                if type(op2) == int:
                    compile_mov(Operand("HELP_REGISTER", op2), Operand("CONSTANT", "0"))
                    helpRegisterScopes[op2] = len(bonInstructions)
                    # help registers might need to be reset

        compiler_functions = {
            "add": compile_add,
            "sub": compile_sub,
            "mov": compile_mov,
            "hlt": compile_hlt,
            "jmp": compile_jmp,
            "cmp": compile_cmp,
        }
        orgLabels = [(line, label) for label, line in self.symbolTable.items() if label[0] == "."]
        orgLabels.sort(key=lambda e: e[0])
        labelHead = 0
        labels = {}
        orgHelpRegisterScopes = [(line, register) for register, line in self.helpRegisterScopes.items()]
        orgHelpRegisterScopes.sort(key=lambda e: e[0])
        helpRegisterScopeHead = 0
        while storage.head < len(self.instructions):
            if orgLabels:
                while orgLabels[labelHead][0] == storage.head:
                    labels[orgLabels[labelHead][1]] = len(bonInstructions)
                    if labelHead < len(orgLabels)-1:
                        labelHead += 1
                    else:
                        break
                # whenever a label points to the current line in the intermediate code
                # it is translated to the current line in the Bonsai code
            instruction = self.instructions[storage.head]
            # the next instruction is fetched
            compiler_functions[instruction.opcode](instruction.op1, instruction.op2)
            # and the corresponding compilation function called
            storage.head += 1
            if orgHelpRegisterScopes:
                while orgHelpRegisterScopes[helpRegisterScopeHead][0] == storage.head:
                    helpRegisterScopes[orgHelpRegisterScopes[helpRegisterScopeHead][1]] = len(bonInstructions)
                    if helpRegisterScopeHead < len(orgHelpRegisterScopes)-1:
                        helpRegisterScopeHead += 1
                    else:
                        break
                # when a help register was last used, the line must be denoted for
                # the actual Bonsai code
        for i, instruction in enumerate(bonInstructions):
            if type(instruction[1]) == int:
                bonInstructions[i] = (instruction[0], ("H", instruction[1]))
                # mark help registers
            elif type(instruction[1]) == str:
                if instruction[1][0] == ".":
                    bonInstructions[i] = (instruction[0], labels[instruction[1]]+1)
                    # replace label with the actual position
                elif instruction[1][0] == "@":
                    bonInstructions[i] = (instruction[0], i+int(instruction[1][1:])+1)
                    # calculate relative addresses
                else:
                    bonInstructions[i] = (instruction[0], self.symbolTable[instruction[1]]+1)
                    # look up register in symbol table
        registerCount = len(self.registers)
        helpRegisterScopes = [(line, register) for register, line in helpRegisterScopes.items()]
        helpRegisterScopes.sort(key=lambda e: e[0])
        helpRegisterScopeHead = 0
        freeHelpRegisters = []
        helpRegistersInUse = {}
        for i, instruction in enumerate(bonInstructions):
            if type(instruction[1]) == tuple:
                # the operand is a help register
                if instruction[1][1] in helpRegistersInUse:
                    helpRegister = helpRegistersInUse[instruction[1][1]]
                    # a help register has already been found and is reused
                elif freeHelpRegisters:
                    helpRegister = freeHelpRegisters.pop()
                    helpRegistersInUse[instruction[1][1]] = helpRegister
                    # there are free help registers that were previously created
                    # use one of them
                else:
                    registerCount += 1
                    helpRegister = registerCount
                    helpRegistersInUse[instruction[1][1]] = helpRegister
                    # there currently aren't any free help registers
                    # create a new one
                bonInstructions[i] = (instruction[0], helpRegister)
            if helpRegisterScopes and i == helpRegisterScopes[helpRegisterScopeHead][0]:
                freeHelpRegisters.append(helpRegistersInUse[helpRegisterScopes[helpRegisterScopeHead][1]])
                del helpRegistersInUse[helpRegisterScopes[helpRegisterScopeHead][1]]
                if helpRegisterScopeHead < len(helpRegisterScopes)-1:
                    helpRegisterScopeHead += 1
                # a previously used help register is now unused
                # free it so that it can be reused
        # join the various parts of the program:
        return "".join(chain((("{}{:2d}\r\n".format(opcode, oprnd) if oprnd is not None else opcode+"  \r\n") for opcode, oprnd in bonInstructions),
                              # the instructions
                              ("#{:5d}\r\n".format(int(register)) for register in self.registers),
                              # user defined registers
                              ("#    0\r\n" for register in freeHelpRegisters),
                              # help registers
                              (";{}\r\n".format(comment) for comment in self.comments),
                              # comments
                              (";\r\n" for i in range(10-len(self.comments)))))
                              # add empty comments so that there are at least 10

Instruction = namedtuple("Instruction", ["opcode", "op1", "op2"])
Operand = namedtuple("Operator", ["typ", "val"])

class CompilerError(Exception):

    """A generic error thrown by the intermediate code generator and compiler."""

    pass