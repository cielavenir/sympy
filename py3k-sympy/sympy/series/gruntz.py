"""
Limits
======

Implemented according to the PhD thesis
http://www.cybertester.com/data/gruntz.pdf, which contains very thorough
descriptions of the algorithm including many examples.  We summarize here the
gist of it.


All functions are sorted according to how rapidly varying they are at infinity
using the following rules. Any two functions f and g can be compared using the
properties of L:

L=lim  log|f(x)| / log|g(x)|           (for x -> oo)

We define >, < ~ according to::

    1. f > g .... L=+-oo

        we say that:
        - f is greater than any power of g
        - f is more rapidly varying than g
        - f goes to infinity/zero faster than g


    2. f < g .... L=0

        we say that:
        - f is lower than any power of g

    3. f ~ g .... L!=0, +-oo

        we say that:
        - both f and g are bounded from above and below by suitable integral
          powers of the other


Examples
========
::
    2 < x < exp(x) < exp(x**2) < exp(exp(x))
    2 ~ 3 ~ -5
    x ~ x**2 ~ x**3 ~ 1/x ~ x**m ~ -x
    exp(x) ~ exp(-x) ~ exp(2x) ~ exp(x)**2 ~ exp(x+exp(-x))
    f ~ 1/f

So we can divide all the functions into comparability classes (x and x^2 belong
to one class, exp(x) and exp(-x) belong to some other class). In principle, we
could compare any two functions, but in our algorithm, we don't compare
anything below the class 2~3~-5 (for example log(x) is below this), so we set
2~3~-5 as the lowest comparability class.

Given the function f, we find the list of most rapidly varying (mrv set)
subexpressions of it. This list belongs to the same comparability class. Let's
say it is {exp(x), exp(2x)}. Using the rule f ~ 1/f we find an element "w"
(either from the list or a new one) from the same comparability class which
goes to zero at infinity. In our example we set w=exp(-x) (but we could also
set w=exp(-2x) or w=exp(-3x) ...). We rewrite the mrv set using w, in our case
{1/w, 1/w^2}, and substitute it into f. Then we expand f into a series in w::

    f = c0*w^e0 + c1*w^e1 + ... + O(w^en),       where e0<e1<...<en, c0!=0

but for x->oo, lim f = lim c0*w^e0, because all the other terms go to zero,
because w goes to zero faster than the ci and ei. So::

    for e0>0, lim f = 0
    for e0<0, lim f = +-oo   (the sign depends on the sign of c0)
    for e0=0, lim f = lim c0

We need to recursively compute limits at several places of the algorithm, but
as is shown in the PhD thesis, it always finishes.

Important functions from the implementation:

compare(a, b, x) compares "a" and "b" by computing the limit L.
mrv(e, x) returns the list of most rapidly varying (mrv) subexpressions of "e"
rewrite(e, Omega, x, wsym) rewrites "e" in terms of w
leadterm(f, x) returns the lowest power term in the series of f
mrv_leadterm(e, x) returns the lead term (c0, e0) for e
limitinf(e, x) computes lim e  (for x->oo)
limit(e, z, z0) computes any limit by converting it to the case x->oo

All the functions are really simple and straightforward except rewrite(), which
is the most difficult/complex part of the algorithm. When the algorithm fails,
the bugs are usually in the series expansion (i.e. in SymPy) or in rewrite.

This code is almost exact rewrite of the Maple code inside the Gruntz thesis.

Debugging
---------

Because the gruntz algorithm is highly recursive, it's difficult to figure out
what went wrong inside a debugger. Instead, turn on nice debug prints by
defining the environment variable SYMPY_DEBUG. For example:

[user@localhost]: SYMPY_DEBUG=True ./bin/isympy

In [1]: limit(sin(x)/x, x, 0)
limitinf(_x*sin(1/_x), _x) = 1
+-mrv_leadterm(_x*sin(1/_x), _x) = (1, 0)
| +-mrv(_x*sin(1/_x), _x) = set([_x])
| | +-mrv(_x, _x) = set([_x])
| | +-mrv(sin(1/_x), _x) = set([_x])
| |   +-mrv(1/_x, _x) = set([_x])
| |     +-mrv(_x, _x) = set([_x])
| +-mrv_leadterm(exp(_x)*sin(exp(-_x)), _x, set([exp(_x)])) = (1, 0)
|   +-rewrite(exp(_x)*sin(exp(-_x)), set([exp(_x)]), _x, _w) = (1/_w*sin(_w), -_x)
|     +-sign(_x, _x) = 1
|     +-mrv_leadterm(1, _x) = (1, 0)
+-sign(0, _x) = 0
+-limitinf(1, _x) = 1

And check manually which line is wrong. Then go to the source code and debug
this function to figure out the exact problem.

"""
from sympy import SYMPY_DEBUG
from sympy.core import Basic, S, oo, Symbol, C, I, Dummy, Wild
from sympy.core.function import Function, UndefinedFunction
from sympy.functions import log, exp
from sympy.series.order import Order
from sympy.simplify import powsimp
from sympy import cacheit

from sympy.core.compatibility import reduce
from functools import reduce

O = Order

def debug(func):
    """Only for debugging purposes: prints a tree

    It will print a nice execution tree with arguments and results
    of all decorated functions.
    """
    if not SYMPY_DEBUG:
        #normal mode - do nothing
        return func

    #debug mode
    def decorated(*args, **kwargs):
        #r = func(*args, **kwargs)
        r = maketree(func, *args, **kwargs)
        #print "%s = %s(%s, %s)" % (r, func.__name__, args, kwargs)
        return r

    return decorated

from time import time
it = 0
do_timings = False
def timeit(func):
    global do_timings
    if not do_timings:
        return func
    def dec(*args, **kwargs):
        global it
        it += 1
        t0 = time()
        r = func(*args, **kwargs)
        t1 = time()
        print("%s %.3f %s%s" % ('-' * (2+it), t1-t0, func.__name__, args))
        it -= 1
        return r
    return dec

def tree(subtrees):
    "Only debugging purposes: prints a tree"
    def indent(s, type=1):
        x = s.split("\n")
        r = "+-%s\n"%x[0]
        for a in x[1:]:
            if a == "":
                continue
            if type == 1:
                r += "| %s\n"%a
            else:
                r += "  %s\n"%a
        return r
    if len(subtrees) == 0:
        return ""
    f = []
    for a in subtrees[:-1]:
        f.append(indent(a))
    f.append(indent(subtrees[-1], 2))
    return ''.join(f)

tmp = []
iter = 0
def maketree(f, *args, **kw):
    "Only debugging purposes: prints a tree"
    global tmp
    global iter
    oldtmp = tmp
    tmp = []
    iter += 1

    # If there is a bug and the algorithm enters an infinite loop, enable the
    # following line. It will print the names and parameters of all major functions
    # that are called, *before* they are called
    #print "%s%s %s%s" % (iter, reduce(lambda x, y: x + y,map(lambda x: '-',range(1,2+iter))), f.func_name, args)

    r = f(*args, **kw)

    iter -= 1
    s = "%s%s = %s\n" % (f.__name__, args, r)
    if tmp != []:
        s += tree(tmp)
    tmp = oldtmp
    tmp.append(s)
    if iter == 0:
        print(tmp[0])
        tmp = []
    return r

def compare(a, b, x):
    """Returns "<" if a<b, "=" for a == b, ">" for a>b"""
    # log(exp(...)) must always be simplified here for termination
    la, lb = log(a), log(b)
    if isinstance(a, Basic) and a.func is exp:
        la = a.args[0]
    if isinstance(b, Basic) and b.func is exp:
        lb = b.args[0]

    c = limitinf(la/lb, x)
    if c == 0:
        return "<"
    elif c.is_unbounded:
        return ">"
    else:
        return "="

class SubsSet(dict):
    """
    Stores (expr, dummy) pairs, and how to rewrite expr-s.

    The gruntz algorithm needs to rewrite certain expressions in term of a new
    variable w. We cannot use subs, because it is just too smart for us. For
    example:
        > Omega=[exp(exp(_p - exp(-_p))/(1 - 1/_p)), exp(exp(_p))]
        > O2=[exp(-exp(_p) + exp(-exp(-_p))*exp(_p)/(1 - 1/_p))/_w, 1/_w]
        > e = exp(exp(_p - exp(-_p))/(1 - 1/_p)) - exp(exp(_p))
        > e.subs(Omega[0],O2[0]).subs(Omega[1],O2[1])
        -1/w + exp(exp(p)*exp(-exp(-p))/(1 - 1/p))
    is really not what we want!

    So we do it the hard way and keep track of all the things we potentially
    want to substitute by dummy variables. Consider the expression
        exp(x - exp(-x)) + exp(x) + x.
    The mrv set is {exp(x), exp(-x), exp(x - exp(-x))}.
    We introduce corresponding dummy variables d1, d2, d3 and rewrite:
        d3 + d1 + x.
    This class first of all keeps track of the mapping expr->variable, i.e.
    will at this stage be a dictionary
        {exp(x): d1, exp(-x): d2, exp(x - exp(-x)): d3}.
    [It turns out to be more convenient this way round.]
    But sometimes expressions in the mrv set have other expressions from the
    mrv set as subexpressions, and we need to keep track of that as well. In
    this case, d3 is really exp(x - d2), so rewrites at this stage is
        {d3: exp(x-d2)}.

    The function rewrite uses all this information to correctly rewrite our
    expression in terms of w. In this case w can be choosen to be exp(-x),
    i.e. d2. The correct rewriting then is
        exp(-w)/w + 1/w + x.
    """
    def __init__(self):
        self.rewrites = {}

    def __repr__(self):
        return super(SubsSet, self).__repr__() + ', ' + self.rewrites.__repr__()

    def __getitem__(self, key):
        if not key in self:
            self[key] = Dummy()
        return dict.__getitem__(self, key)

    def do_subs(self, e):
        for expr, var in self.items():
            e = e.subs(var, expr)
        return e

    def meets(self, s2):
        """ Tell whether or not self and s2 have non-empty intersection """
        return set(self.keys()).intersection(list(s2.keys())) != set()

    def union(self, s2, exps=None):
        """ Compute the union of self and s2, adjusting exps """
        res = self.copy()
        tr = {}
        for expr, var in s2.items():
            if expr in self:
                if exps: exps = exps.subs(var, res[expr])
                tr[var] = res[expr]
            else:
                res[expr] = var
        for var, rewr in s2.rewrites.items():
            res.rewrites[var] = rewr.subs(tr)
        return res, exps

    def copy(self):
        r = SubsSet()
        r.rewrites = self.rewrites.copy()
        for expr, var in self.items():
            r[expr] = var
        return r

@debug
def mrv(e, x):
    """Returns a SubsSet of  most rapidly varying (mrv) subexpressions of 'e',
       and e rewritten in terms of these"""
    e = powsimp(e, deep=True, combine='exp')
    assert isinstance(e, Basic)
    if not e.has(x):
        return SubsSet(), e
    elif e == x:
        s = SubsSet()
        return s, s[x]
    elif e.is_Mul or e.is_Add:
        i, d = e.as_independent(x) # throw away x-independent terms
        if d.func != e.func:
            s, expr = mrv(d, x)
            return s, e.func(i, expr)
        a, b = d.as_two_terms()
        s1, e1 = mrv(a, x)
        s2, e2 = mrv(b, x)
        return mrv_max1(s1, s2, e.func(i, e1, e2), x)
    elif e.is_Pow:
        b, e = e.as_base_exp()
        if e.has(x):
            return mrv(exp(e * log(b)), x)
        else:
            s, expr = mrv(b, x)
            return s, expr**e
    elif e.func is log:
        s, expr = mrv(e.args[0], x)
        return s, log(expr)
    elif e.func is exp:
        # We know from the theory of this algorithm that exp(log(...)) may always
        # be simplified here, and doing so is vital for termination.
        if e.args[0].func is log:
            return mrv(e.args[0].args[0], x)
        if limitinf(e.args[0], x).is_unbounded:
            s1 = SubsSet()
            e1 = s1[e]
            s2, e2 = mrv(e.args[0], x)
            su = s1.union(s2)[0]
            su.rewrites[e1] = exp(e2)
            return mrv_max3(s1, e1, s2, exp(e2), su, e1, x)
        else:
            s, expr = mrv(e.args[0], x)
            return s, exp(expr)
    elif e.is_Function:
        l = [mrv(a, x) for a in e.args]
        l2 = [s for (s, _) in l if s != SubsSet()]
        if len(l2) != 1:
            # e.g. something like BesselJ(x, x)
            raise NotImplementedError("MRV set computation for functions in"
                                      " several variables not implemented.")
        s, ss = l2[0], SubsSet()
        args = [ss.do_subs(x[1]) for x in l]
        return s, e.func(*args)
    elif e.is_Derivative:
        raise NotImplementedError("MRV set computation for derviatives"
                                  " not implemented yet.")
        return mrv(e.args[0], x)
    raise NotImplementedError("Don't know how to calculate the mrv of '%s'" % e)

def mrv_max3(f, expsf, g, expsg, union, expsboth, x):
    """Computes the maximum of two sets of expressions f and g, which
    are in the same comparability class, i.e. max() compares (two elements of)
    f and g and returns either (f, expsf) [if f is larger], (g, expsg)
    [if g is larger] or (union, expsboth) [if f, g are of the same class].
    """
    assert isinstance(f, SubsSet)
    assert isinstance(g, SubsSet)

    if f == SubsSet():
        return g, expsg
    elif g == SubsSet():
        return f, expsf
    elif f.meets(g):
        return union, expsboth

    c = compare(list(f.keys())[0], list(g.keys())[0], x)
    if c == ">":
        return f, expsf
    elif c == "<":
        return g, expsg
    else:
        assert c == "="
        return union, expsboth

def mrv_max1(f, g, exps, x):
    """Computes the maximum of two sets of expressions f and g, which
    are in the same comparability class, i.e. mrv_max1() compares (two elements of)
    f and g and returns the set, which is in the higher comparability class
    of the union of both, if they have the same order of variation.
    Also returns exps, with the appropriate substitutions made.
    """
    u, b = f.union(g, exps)
    return mrv_max3(f, g.do_subs(exps), g, f.do_subs(exps),
                    u, b, x)

@debug
@cacheit
@timeit
def sign(e, x):
    """Returns a sign of an expression e(x) for x->oo.

        e >  0 for x sufficiently large ...  1
        e == 0 for x sufficiently large ...  0
        e <  0 for x sufficiently large ... -1

        The result of this function is currently undefined if e changes sign
        arbitarily often for arbitrarily large x (e.g. sin(x)).

       Note that this returns zero only if e is *constantly* zero
       for x sufficiently large. [If e is constant, of course, this is just
       the same thing as the sign of e.]
    """
    from sympy import sign as _sign
    assert isinstance(e, Basic)

    if e.is_positive:
        return 1
    elif e.is_negative:
        return -1

    if e.is_Rational or e.is_Float:
        assert not e is S.NaN
        if e == 0:
            return 0
        elif e.evalf() > 0:
            return 1
        else:
            return -1
    elif not e.has(x):
        return _sign(e)
    elif e == x:
        return 1
    elif e.is_Mul:
        a, b = e.as_two_terms()
        sa = sign(a, x)
        if not sa:
            return 0
        return sa * sign(b, x)
    elif e.func is exp:
        return 1
    elif e.is_Pow:
        s = sign(e.base, x)
        if s == 1:
            return 1
        if e.exp.is_Integer:
            return s**e.exp
    elif e.func is log:
        return sign(e.args[0] -1, x)

    # if all else fails, do it the hard way
    c0, e0 = mrv_leadterm(e, x)
    return sign(c0, x)

@debug
@timeit
@cacheit
def limitinf(e, x):
    """Limit e(x) for x-> oo"""
    #rewrite e in terms of tractable functions only
    e = e.rewrite('tractable', deep=True)

    if not e.has(x):
        return e #e is a constant
    if not x.is_positive:
        # We make sure that x.is_positive is True so we
        # get all the correct mathematical bechavior from the expression.
        # We need a fresh variable.
        p = Dummy('p', positive=True, bounded=True)
        e = e.subs(x, p)
        x = p
    c0, e0 = mrv_leadterm(e, x)
    sig = sign(e0, x)
    if sig == 1:
        return S.Zero # e0>0: lim f = 0
    elif sig == -1: #e0<0: lim f = +-oo (the sign depends on the sign of c0)
        if c0.match(I*Wild("a", exclude=[I])):
            return c0*oo
        s = sign(c0, x)
        #the leading term shouldn't be 0:
        assert s != 0
        return s*oo
    elif sig == 0:
        return limitinf(c0, x) #e0=0: lim f = lim c0

def moveup2(s, x):
    r = SubsSet()
    for expr, var in s.items():
        r[expr.subs(x, exp(x))] = var
    for var, expr in s.rewrites.items():
        r.rewrites[var] = s.rewrites[var].subs(x, exp(x))
    return r

def moveup(l, x):
    return [e.subs(x, exp(x)) for e in l]


@debug
@timeit
def calculate_series(e, x, skip_abs=False, logx=None):
    """ Calculates at least one term of the series of "e" in "x".

    This is a place that fails most often, so it is in its own function.
    """

    f = e
    for n in [1, 2, 4, 6, 8]:
        series = f.nseries(x, n=n, logx=logx)
        if not series.has(O):
            # The series expansion is locally exact.
            return series

        series = series.removeO()
        if series:
            if (not skip_abs) or series.has(x):
                break
    else:
        raise ValueError('(%s).series(%s, n=8) gave no terms.' % (f, x))
    return series

@debug
@timeit
@cacheit
def mrv_leadterm(e, x):
    """Returns (c0, e0) for e."""
    Omega = SubsSet()
    if not e.has(x):
        return (e, S.Zero)
    if Omega == SubsSet():
        Omega, exps = mrv(e, x)
    if not Omega:
        # e really does not depend on x after simplification
        series = calculate_series(e, x)
        c0, e0 = series.leadterm(x)
        assert e0 == 0
        return c0, e0
    if x in Omega:
        #move the whole omega up (exponentiate each term):
        Omega_up = moveup2(Omega, x)
        e_up = moveup([e], x)[0]
        exps_up = moveup([exps], x)[0]
        # NOTE: there is no need to move this down!
        e = e_up
        Omega = Omega_up
        exps = exps_up
    #
    # The positive dummy, w, is used here so log(w*2) etc. will expand;
    # a unique dummy is needed in this algorithm
    #
    # For limits of complex functions, the algorithm would have to be
    # improved, or just find limits of Re and Im components separately.
    #
    w = Dummy("w", real=True, positive=True, bounded=True)
    f, logw = rewrite(exps, Omega, x, w)
    series = calculate_series(f, w, logx=logw)
    series = series.subs(log(w), logw) # this should not be necessary
    return series.leadterm(w)

def build_expression_tree(Omega, rewrites):
    """ Helper function for rewrite.

    We need to sort Omega (mrv set) so that we replace an expression before
    we replace any expression in terms of which it has to be rewritten:
    e1 ---> e2 ---> e3
             \
              -> e4
    Here we can do e1, e2, e3, e4 or e1, e2, e4, e3.
    To do this we assemble the nodes into a tree, and sort them by height.

    This function builds the tree, rewrites then sorts the nodes.
    """
    class Node:
        def ht(self):
            return reduce(lambda x, y: x + y,
                          [x.ht() for x in self.before], 1)
    nodes = {}
    for expr, v in Omega:
        n = Node()
        n.before = []
        n.var = v
        n.expr = expr
        nodes[v] = n
    for _, v in Omega:
        if v in rewrites:
            n = nodes[v]
            r = rewrites[v]
            for _, v2 in Omega:
                if r.has(v2):
                    n.before.append(nodes[v2])

    return nodes

@debug
@timeit
def rewrite(e, Omega, x, wsym):
    """e(x) ... the function
    Omega ... the mrv set
    wsym ... the symbol which is going to be used for w

    Returns the rewritten e in terms of w and log(w). See test_rewrite1()
    for examples and correct results.
    """
    assert isinstance(Omega, SubsSet)
    assert len(Omega) != 0
    #all items in Omega must be exponentials
    for t in list(Omega.keys()):
        assert t.func is exp
    rewrites = Omega.rewrites
    Omega = list(Omega.items())

    nodes = build_expression_tree(Omega, rewrites)
    Omega.sort(key=lambda x: nodes[x[1]].ht(), reverse=True)

    g, _ = Omega[-1] #g is going to be the "w" - the simplest one in the mrv set
    sig = sign(g.args[0], x)
    if sig == 1:
        wsym = 1/wsym #if g goes to oo, substitute 1/w
    elif sig != -1:
        raise NotImplementedError('Result depends on the sign of %s' % sig)
    #O2 is a list, which results by rewriting each item in Omega using "w"
    O2 = []
    for f, var in Omega:
        c = limitinf(f.args[0]/g.args[0], x)
        arg = f.args[0]
        if var in rewrites:
            assert rewrites[var].func is exp
            arg = rewrites[var].args[0]
        O2.append((var, exp((arg - c*g.args[0]).expand())*wsym**c))

    #Remember that Omega contains subexpressions of "e". So now we find
    #them in "e" and substitute them for our rewriting, stored in O2

    # the following powsimp is necessary to automatically combine exponentials,
    # so that the .subs() below succeeds:
    # TODO this should not be necessary
    f = powsimp(e, deep=True, combine='exp')
    for a, b in O2:
        f = f.subs(a, b)

    for _, var in Omega:
        assert not f.has(var)

    #finally compute the logarithm of w (logw).
    logw = g.args[0]
    if sig == 1:
        logw = -logw     #log(w)->log(1/w)=-log(w)

    return f, logw

def gruntz(e, z, z0, dir="+"):
    """
    Compute the limit of e(z) at the point z0 using the Gruntz algorithm.

    z0 can be any expression, including oo and -oo.

    For dir="+" (default) it calculates the limit from the right
    (z->z0+) and for dir="-" the limit from the left (z->z0-). For infinite z0
    (oo or -oo), the dir argument doesn't matter.

    This algorithm is fully described in the module docstring in the gruntz.py
    file. It relies heavily on the series expansion. Most frequently, gruntz()
    is only used if the faster limit() function (which uses heuristics) fails.
    """
    if not isinstance(z, Symbol):
        raise NotImplementedError("Second argument must be a Symbol")

    #convert all limits to the limit z->oo; sign of z is handled in limitinf
    r = None
    if z0 == oo:
        r = limitinf(e, z)
    elif z0 == -oo:
        r = limitinf(e.subs(z, -z), z)
    else:
        if dir == "-":
            e0 = e.subs(z, z0 - 1/z)
        elif dir == "+":
            e0 = e.subs(z, z0 + 1/z)
        else:
            raise NotImplementedError("dir must be '+' or '-'")
        r = limitinf(e0, z)

    # This is a bit of a heuristic for nice results... we always rewrite
    # tractable functions in terms of familiar intractable ones.
    # It might be nicer to rewrite the exactly to what they were initially,
    # but that would take some work to implement.
    return r.rewrite('intractable', deep=True)
