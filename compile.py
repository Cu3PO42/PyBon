"""
Main compilation module.

Exports:
    compilePB: func - compile Python Bonsai code
"""

from lexer import Lexer
from syntactic_analyzer import SyntacticAnalysis
from semantic_analyzer import SemanticAnalysis
from intermediate_code import IntermediateCode
from optimizer import Optimizer
from sys import stderr

def compilePB(pyBonCode: str, verbosity=0) -> str:
    """Compile Python Bonsai code and return Bonsai code.

    This function combines the various stages of the compiler and optionally outputs the interim stages.
    The stages called are (in order):
        - Lexer
        - Syntactic Analyzer (Parser)
        - Semantic Analyzer
        - Intermediate Code Generator
        - Optimizer
        - Intermediate Code Compiler

    Parameters:
        @param pyBonCode: the Python Bonsai code to be compiled as raw source
        @param verbosity: the verbosity level defines which interim stages to print

        @type pyBonCode: str
        @type verbosity: int
    """
    if verbosity is None:
        verbosity = 0
    tokens = Lexer(pyBonCode).tokens()
    if verbosity > 1:
        print("Tokens:", file=stderr)
        for token in tokens:
            print(token, file=stderr)
        print("", file=stderr)
    ast = SyntacticAnalysis(tokens)
    SemanticAnalysis(ast)
    ic = IntermediateCode()
    ic.fromSyntaxTree(ast)
    if verbosity > 2:
        print("Original instructions:", file=stderr)
        _print_instructions(ic)
        print("\nSymbols:", file=stderr)
        print(ic.symbolTable, file=stderr)
        print("\nRegisters:", file=stderr)
        print(ic.registers, file=stderr)
    oc = Optimizer(ic)
    bonCode = oc.compile()
    if verbosity > 0:
        print("\nOptimized instructions:", file=stderr)
        _print_instructions(oc)
        print("\nSymbols:", file=stderr)
        print(oc.symbolTable, file=stderr)
        print("\nRegisters:", file=stderr)
        print(oc.registers, file=stderr)
        print("\nCompiled Bonsai code:", file=stderr)
        print(bonCode, file=stderr)
    return bonCode

def _print_instructions(ic):

    """
    Print the instructions from the given intermediate code.

    Arguments:
        @param ic: the intermediate code whose instructions to print
        @type ic: IntermediateCode
    """

    def formatOperand(op):
        return {
            "REGISTER": "%",
            "HELP_REGISTER": "%",
            "LABEL_IDENTIFIER": "",
            "CONSTANT": "$"
        }[op.typ] + str(op.val)

    instructionStrings = []
    for instruction in ic.instructions:
        instructionStrings.append(
            instruction.opcode.ljust(3) +
            (" " + formatOperand(instruction.op1) +
             (", " + formatOperand(instruction.op2) if instruction.op2 else "")
             if instruction.op1 else "")
        )
    labels = dict((int(line), label) for label, line in ic.symbolTable.items() if label[0] == ".")
    max_length = max(map(lambda e: len(e[1]), labels.items()))
    for i, instruction in enumerate(instructionStrings):
        print(
            labels.get(i, "").rjust(max_length),
            instruction,
            file=stderr
        )
