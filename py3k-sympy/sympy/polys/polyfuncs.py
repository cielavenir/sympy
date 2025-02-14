"""High-level polynomials manipulation functions. """

from sympy.polys.polytools import (
    poly_from_expr, parallel_poly_from_expr, Poly)
from sympy.polys.polyoptions import allowed_flags

from sympy.polys.specialpolys import (
    symmetric_poly, interpolating_poly)

from sympy.polys.polyerrors import (
    PolificationFailed, ComputationFailed,
    MultivariatePolynomialError)

from sympy.utilities import numbered_symbols, take

from sympy.core import S, Basic, Add, Mul

def symmetrize(F, *gens, **args):
    """
    Rewrite a polynomial in terms of elementary symmetric polynomials.

    **Examples**

    >>> from sympy.polys.polyfuncs import symmetrize
    >>> from sympy.abc import x, y

    >>> symmetrize(x**2 + y**2)
    (-2*x*y + (x + y)**2, 0)

    >>> symmetrize(x**2 + y**2, formal=True)
    (s1**2 - 2*s2, 0, [(s1, x + y), (s2, x*y)])

    >>> symmetrize(x**2 - y**2)
    (-2*x*y + (x + y)**2, -2*y**2)

    >>> symmetrize(x**2 - y**2, formal=True)
    (s1**2 - 2*s2, -2*y**2, [(s1, x + y), (s2, x*y)])

    """
    allowed_flags(args, ['formal', 'symbols'])

    iterable = True

    if not hasattr(F, '__iter__'):
        iterable = False
        F = [F]

    try:
        F, opt = parallel_poly_from_expr(F, *gens, **args)
    except PolificationFailed as exc:
        result = []

        for expr in exc.exprs:
            if expr.is_Number:
                result.append((expr, S.Zero))
            else:
                raise ComputationFailed('symmetrize', len(F), exc)
        else:
            if not iterable:
                result, = result

            if not exc.opt.formal:
                return result
            else:
                if iterable:
                    return result, []
                else:
                    return result + ([],)

    polys, symbols = [], opt.symbols
    gens, dom = opt.gens, opt.domain

    for i in range(0, len(gens)):
        poly = symmetric_poly(i+1, gens, polys=True)
        polys.append((next(symbols), poly.set_domain(dom)))

    indices = list(range(0, len(gens) - 1))
    weights = list(range(len(gens), 0, -1))

    result = []

    for f in F:
        symmetric = []

        if not f.is_homogeneous:
            symmetric.append(f.TC())
            f -= f.TC()

        while f:
            _height, _monom, _coeff = -1, None, None

            for i, (monom, coeff) in enumerate(f.terms()):
                if all(monom[i] >= monom[i+1] for i in indices):
                    height = max([ n*m for n, m in zip(weights, monom) ])

                    if height > _height:
                        _height, _monom, _coeff = height, monom, coeff

            if _height != -1:
                monom, coeff = _monom, _coeff
            else:
                break

            exponents = []

            for m1, m2 in zip(monom, monom[1:] + (0,)):
                exponents.append(m1 - m2)

            term = [ s**n for (s, _), n in zip(polys, exponents) ]
            poly = [ p**n for (_, p), n in zip(polys, exponents) ]

            symmetric.append(Mul(coeff, *term))
            product = poly[0].mul(coeff)

            for p in poly[1:]:
                product = product.mul(p)

            f -= product

        result.append((Add(*symmetric), f.as_expr()))

    polys = [ (s, p.as_expr()) for s, p in polys ]

    if not opt.formal:
        for i, (sym, non_sym) in enumerate(result):
            result[i] = (sym.subs(polys), non_sym)

    if not iterable:
        result, = result

    if not opt.formal:
        return result
    else:
        if iterable:
            return result, polys
        else:
            return result + (polys,)

def horner(f, *gens, **args):
    """
    Rewrite a polynomial in Horner form.

    **Examples**

    >>> from sympy.polys.polyfuncs import horner
    >>> from sympy.abc import x, y, a, b, c, d, e

    >>> horner(9*x**4 + 8*x**3 + 7*x**2 + 6*x + 5)
    x*(x*(x*(9*x + 8) + 7) + 6) + 5

    >>> horner(a*x**4 + b*x**3 + c*x**2 + d*x + e)
    e + x*(d + x*(c + x*(a*x + b)))

    >>> f = 4*x**2*y**2 + 2*x**2*y + 2*x*y**2 + x*y

    >>> horner(f, wrt=x)
    x*(x*y*(4*y + 2) + y*(2*y + 1))

    >>> horner(f, wrt=y)
    y*(x*y*(4*x + 2) + x*(2*x + 1))

    """
    allowed_flags(args, [])

    try:
        F, opt = poly_from_expr(f, *gens, **args)
    except PolificationFailed as exc:
        return exc.expr

    form, gen = S.Zero, F.gen

    if F.is_univariate:
        for coeff in F.all_coeffs():
            form = form*gen + coeff
    else:
        F, gens = Poly(F, gen), gens[1:]

        for coeff in F.all_coeffs():
            form = form*gen + horner(coeff, *gens, **args)

    return form

def interpolate(data, x):
    """
    Construct an interpolating polynomial for the data points.

    **Examples**

    >>> from sympy.polys.polyfuncs import interpolate
    >>> from sympy.abc import x

    >>> interpolate([1, 4, 9, 16], x)
    x**2
    >>> interpolate([(1, 1), (2, 4), (3, 9)], x)
    x**2
    >>> interpolate([(1, 2), (2, 5), (3, 10)], x)
    x**2 + 1
    >>> interpolate({1: 2, 2: 5, 3: 10}, x)
    x**2 + 1

    """
    n = len(data)

    if isinstance(data, dict):
        X, Y = list(zip(*list(data.items())))
    else:
        if isinstance(data[0], tuple):
            X, Y = list(zip(*data))
        else:
            X = list(range(1, n+1))
            Y = list(data)

    poly = interpolating_poly(n, x, X, Y)

    return poly.expand()

def viete(f, roots=None, *gens, **args):
    """
    Generate Viete's formulas for ``f``.

    **Examples**

    >>> from sympy.polys.polyfuncs import viete
    >>> from sympy import symbols

    >>> x, a, b, c, r1, r2 = symbols('x,a:c,r1:3')

    >>> viete(a*x**2 + b*x + c, [r1, r2], x)
    [(r1 + r2, -b/a), (r1*r2, c/a)]

    """
    allowed_flags(args, [])

    if isinstance(roots, Basic):
        gens, roots = (roots,) + gens, None

    try:
        f, opt = poly_from_expr(f, *gens, **args)
    except PolificationFailed as exc:
        raise ComputationFailed('viete', 1, exc)

    if f.is_multivariate:
        raise MultivariatePolynomialError("multivariate polynomials are not allowed")

    n = f.degree()

    if n < 1:
        raise ValueError("can't derive Viete's formulas for a constant polynomial")

    if roots is None:
        roots = numbered_symbols('r', start=1)

    roots = take(roots, n)

    if n != len(roots):
        raise ValueError("required %s roots, got %s" % (n, len(roots)))

    lc, coeffs = f.LC(), f.all_coeffs()
    result, sign = [], -1

    for i, coeff in enumerate(coeffs[1:]):
        poly = symmetric_poly(i+1, roots)
        coeff = sign*(coeff/lc)
        result.append((poly, coeff))
        sign = -sign

    return result
