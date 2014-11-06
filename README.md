# PyBon
## An unneccessary compiler

This compiles a very very limited subset of Python to the Bonsai language.

The Bonsai language is the language understood by the "Bonsai educational computer".  
It consists of five instructions:

* **INC**, increments a register
* **DEC**, decrements a register
* **JMP**, unconditional jump to a line of code
* **TST**, tests register against zero and branches
* **HLT**, halts execution

The subset of Python you can use features `if-else` statements with a single non-composite condition, additions, substractions and simple loops over a variable. All variables need to be decalred at the beginning of the file with an assignment of a integer value. Only integer values are supported due to the limits of the underlying language.  
I know this really isn't much, but given the four very simple instructions I can work with, it's pretty great, I think.

## Usage

Please refer to `py2bon.py --help` for usage instructions.

Be warned. The ouput files are HUGE compared to the input. Expect growth by factor 10 or more, depending on complexity of the input.

## License

(C) 2013-2014 Tobias Zimmermann. You may obtain a copy of this software and use it for personal use only. All other rights reserved.

