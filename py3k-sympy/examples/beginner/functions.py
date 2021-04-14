#!/usr/bin/env python3

"""Functions example

Demonstrates sympy defined functions.
"""

import sympy
from sympy import pprint

def main():
    a = sympy.Symbol('a')
    b = sympy.Symbol('b')
    e = sympy.log((a + b)**5)
    print()
    pprint(e)
    print('\n')

    e = sympy.exp(e)
    pprint(e)
    print('\n')

    e = sympy.log(sympy.exp((a + b)**5))
    pprint(e)
    print()

if __name__ == "__main__":
    main()
