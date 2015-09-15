#!/usr/bin/env python3

"""
Py2Bon - Compiles Python-like code to Bonsai Assembler.
This file provides a CLI to the compiler.

(C) 2013 Tobias Zimmermann
"""

import argparse
import os
import re
from compile import compilePB

def main():
    """Parse command line arguments and invoke compilation."""
    parser = argparse.ArgumentParser(description="Compile a Python program to Bonsai assembler.",
                                     epilog="This compiler has supercow powers.")
    parser.add_argument("-v", "--verbose", action="count", help="specify the verbosity level")
    parser.add_argument("-p", "--print", action="store_true", help="print Bonsai program to console")
    out_group = parser.add_mutually_exclusive_group()
    out_group.add_argument("-o", "--out", metavar="PATH", help="output file, defaults to name of input")
    out_group.add_argument("-k", "--keep", action="store_false", help="keep local filesystem; invoke with -p")
    parser.add_argument("file", help="the file to compile")
    args = parser.parse_args()
    filename = os.path.join(os.getcwd(), args.file)
    if os.path.isfile(filename):
        with open(filename, "r") as file:
            pyProg = file.read()
        bonProg = compilePB(pyProg, args.verbose)
        if args.keep:
            if args.out:
                outname = args.out
            else:
                outname = os.path.join(os.path.basename(filename), re.search(r"(?:.*[/\\])?(.+)\..+?$", args.file).group(1)+".bon")
            with open(outname, "w", newline="") as file:
                file.write(bonProg)
        if args.print:
            print(bonProg, end="")
    else:
        print("The file {} does not exist.".format(args.file))

if __name__ == "__main__":
    main()
