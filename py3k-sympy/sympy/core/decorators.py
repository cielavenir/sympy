"""
SymPy core decorators.

The purpose of this module is to expose decorators without any other
dependencies, so that they can be easily imported anywhere in sympy/core.
"""
from .sympify import SympifyError, sympify
import warnings

try:
    from functools import wraps
except ImportError:
    def wraps(old_func):
        """Copy private data from ``old_func`` to ``new_func``. """
        def decorate(new_func):
            new_func.__dict__.update(old_func.__dict__)
            new_func.__module__ = old_func.__module__
            new_func.__name__   = old_func.__name__
            new_func.__doc__    = old_func.__doc__
            return new_func
        return decorate

def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""
    @wraps(func)
    def new_func(*args, **kwargs):
        warnings.warn("Call to deprecated function %s." % func.__name__,
                      category=DeprecationWarning)
        return func(*args, **kwargs)
    return new_func

def _sympifyit(arg, retval=None):
    """decorator to smartly _sympify function arguments

       @_sympifyit('other', NotImplemented)
       def add(self, other):
           ...

       In add, other can be thought of as already being a SymPy object.

       If it is not, the code is likely to catch an exception, then other will
       be explicitly _sympified, and the whole code restarted.

       if _sympify(arg) fails, NotImplemented will be returned

       see: __sympifyit
    """
    def deco(func):
        return __sympifyit(func, arg, retval)

    return deco

def __sympifyit(func, arg, retval=None):
    """decorator to _sympify `arg` argument for function `func`

       don't use directly -- use _sympifyit instead
    """

    # we support f(a,b) only
    assert func.__code__.co_argcount
    # only b is _sympified
    assert func.__code__.co_varnames[1] == arg

    if retval is None:
        @wraps(func)
        def __sympifyit_wrapper(a, b):
            return func(a, sympify(b, strict=True))

    else:
        @wraps(func)
        def __sympifyit_wrapper(a, b):
            try:
                return func(a, sympify(b, strict=True))
            except SympifyError:
                return retval

    return __sympifyit_wrapper


def call_highest_priority(method_name):
    """A decorator for binary special methods to handle _op_priority.

    Binary special methods in Expr and its subclasses use a special attribute
    '_op_priority' to determine whose special method will be called to
    handle the operation. In general, the object having the highest value of
    '_op_priority' will handle the operation. Expr and subclasses that define
    custom binary special methods (__mul__, etc.) should decorate those
    methods with this decorator to add the priority logic.

    The ``method_name`` argument is the name of the method of the other class
    that will be called.  Use this decorator in the following manner::

        # Call other.__rmul__ if other._op_priority > self._op_priority
        @call_highest_priority('__rmul__')
        def __mul__(self, other):
            ...

        # Call other.__mul__ if other._op_priority > self._op_priority
        @call_highest_priority('__mul__')
        def __rmul__(self, other):
        ...
    """
    def priority_decorator(func):
        def binary_op_wrapper(self, other):
            if hasattr(other, '_op_priority'):
                if other._op_priority > self._op_priority:
                    try:
                        f = getattr(other, method_name)
                    except AttributeError:
                        pass
                    else:
                        return f(self)
            return func(self, other)
        return binary_op_wrapper
    return priority_decorator
