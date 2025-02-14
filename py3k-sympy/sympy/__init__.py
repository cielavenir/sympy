"""
SymPy is a Python library for symbolic mathematics. It aims to become a
full-featured computer algebra system (CAS) while keeping the code as simple as
possible in order to be comprehensible and easily extensible. SymPy is written
entirely in Python and does not require any external libraries, except
optionally for plotting support.

See the webpage for more information and documentation:

    http://code.google.com/p/sympy/"""

__version__ = "0.7.1"

def __sympy_debug():
    # helper function so we don't import os globally
    import os
    return eval(os.getenv('SYMPY_DEBUG', 'False'))
SYMPY_DEBUG = __sympy_debug()

from sympy.core import *
from .logic import *
from .assumptions import *
from .polys import *
from .series import *
from .functions import *
from .ntheory import *
from .concrete import *
from .simplify import *
from .solvers import *
from .matrices import *
from .geometry import *
from .utilities import *
from .integrals import *
from .tensor import *
from .parsing import *
# This module is slow to import:
#from physics import units
from .plotting import Plot, textplot
from .printing import pretty, pretty_print, pprint, pprint_use_unicode, \
    pprint_try_use_unicode, print_gtk, print_tree
from .printing import ccode, fcode, latex, preview
from .printing import python, print_python, srepr, sstr, sstrrepr
from .interactive import init_session, init_printing

evalf._create_evalf_table()

# This is slow to import:
#import abc
