"""The module helps converting sympy expressions into shorter forms of them.

for example:
the expression E**(pi*I) will be converted into -1
the expression (x+x)**2 will be converted into 4*x**2
"""
from .simplify import collect, rcollect, separate, radsimp, ratsimp, fraction, \
    simplify, trigsimp, powsimp, combsimp, hypersimp, hypersimilar, nsimplify, \
    logcombine, separatevars, numer, denom, powdenest, posify

from .sqrtdenest import sqrtdenest

from .cse_main import cse

from .traversaltools import use

from .epathtools import epath, EPath

from .hyperexpand import hyperexpand
