"""
The optimizer for Python Bonsai.

Exports:
    Optimizer: func - optimize intermediate code
"""

from intermediate_code import Instruction, Operand
from copy import deepcopy

def Optimizer(ic):

    """
    Optimize intermediate code and return the new code.

    This function applies several optimizations to the intermediate code
    that do not change the functionality but make it shorter and faster to
    execute. All optimizations are in their own wrapped function. They are
    applied until the code is not changed anymore.

    Arguments:
        @param ic: the IntermediateCode object to be optimized

        @type ic: IntermediateCode

    @return: the optimized intermediate code
    @rtype: IntermediateCode
    """

    ic = deepcopy(ic)

    def optimizeJmpToJmp():
        for i, instruction in enumerate(ic.instructions):
            if (instruction.opcode in ["jmp", "jg", "jge", "jl", "jle", "je", "jne"] and
                ic.instructions[ic.symbolTable[instruction.op1.val]].opcode == "jmp"):
                ic.instructions[i] = instruction._replace(op1=ic.instructions[ic.symbolTable[instruction.op1.val]].op1)
                # if jumping to an unconditional jump one can directly jump to the line
                # pointed to by the second jump

    def optimizeJmpToHlt():
        for i, instruction in enumerate(ic.instructions):
            if (instruction.opcode == "jmp" and
                ic.instructions[ic.symbolTable[instruction.op1.val]].opcode == "hlt"):
                ic.instructions[i] = Instruction("hlt", None, None)
                # an unconditional jump to a hlt can be replaced by a hlt

    def optimizeJmpToNextLine():
        i = 0
        while i < len(ic.instructions):
            instruction = ic.instructions[i]
            if (instruction.opcode in ["jmp", "jg", "jge", "jl", "jle", "je", "jne"] and
                ic.symbolTable[instruction.op1.val] == i+1):
                ic.instructions.pop(i)
                # any jump to the next line is unnecessary and will have no effect
                # and can therefore be deleted
                for label in ic.symbolTable:
                    if label[0] == ".":
                        if ic.symbolTable[label] > i:
                            ic.symbolTable[label] -= 1
                        # labels need to be adjusted to the new line constellation
            else:
                i += 1

    optimizations = [optimizeJmpToJmp, optimizeJmpToHlt, optimizeJmpToNextLine]
    old_instructions = None
    while old_instructions != ic.instructions:
        # apply optimizations until the intermediate code doesn't change
        old_instructions = deepcopy(ic.instructions)
        for optimization in optimizations:
            optimization()
    return ic