"""Efficient functions for generating orthogonal polynomials. """

from sympy import Dummy

from sympy.utilities import cythonized

from sympy.polys.constructor import construct_domain
from sympy.polys.polytools import Poly, PurePoly
from sympy.polys.polyclasses import DMP

from sympy.polys.densearith import (
    dup_mul, dup_mul_ground, dup_lshift, dup_sub
)

from sympy.polys.domains import ZZ, QQ

@cythonized("n,i")
def dup_chebyshevt(n, K):
    """Low-level implementation of Chebyshev polynomials of the 1st kind. """
    seq = [[K.one], [K.one, K.zero]]

    for i in range(2, n+1):
        a = dup_mul_ground(dup_lshift(seq[-1], 1, K), K(2), K)
        seq.append(dup_sub(a, seq[-2], K))

    return seq[n]

def chebyshevt_poly(n, x=None, **args):
    """Generates Chebyshev polynomial of the first kind of degree `n` in `x`. """
    if n < 0:
        raise ValueError("can't generate 1st kind Chebyshev polynomial of degree %s" % n)

    poly = DMP(dup_chebyshevt(int(n), ZZ), ZZ)

    if x is not None:
        poly = Poly.new(poly, x)
    else:
        poly = PurePoly.new(poly, Dummy('x'))

    if not args.get('polys', False):
        return poly.as_expr()
    else:
        return poly

@cythonized("n,i")
def dup_chebyshevu(n, K):
    """Low-level implementation of Chebyshev polynomials of the 2nd kind. """
    seq = [[K.one], [K(2), K.zero]]

    for i in range(2, n+1):
        a = dup_mul_ground(dup_lshift(seq[-1], 1, K), K(2), K)
        seq.append(dup_sub(a, seq[-2], K))

    return seq[n]

def chebyshevu_poly(n, x=None, **args):
    """Generates Chebyshev polynomial of the second kind of degree `n` in `x`. """
    if n < 0:
        raise ValueError("can't generate 2nd kind Chebyshev polynomial of degree %s" % n)

    poly = DMP(dup_chebyshevu(int(n), ZZ), ZZ)

    if x is not None:
        poly = Poly.new(poly, x)
    else:
        poly = PurePoly.new(poly, Dummy('x'))

    if not args.get('polys', False):
        return poly.as_expr()
    else:
        return poly

@cythonized("n,i")
def dup_hermite(n, K):
    """Low-level implementation of Hermite polynomials. """
    seq = [[K.one], [K(2), K.zero]]

    for i in range(2, n+1):
        a = dup_lshift(seq[-1], 1, K)
        b = dup_mul_ground(seq[-2], K(i-1), K)

        c = dup_mul_ground(dup_sub(a, b, K), K(2), K)

        seq.append(c)

    return seq[n]

def hermite_poly(n, x=None, **args):
    """Generates Hermite polynomial of degree `n` in `x`. """
    if n < 0:
        raise ValueError("can't generate Hermite polynomial of degree %s" % n)

    poly = DMP(dup_hermite(int(n), ZZ), ZZ)

    if x is not None:
        poly = Poly.new(poly, x)
    else:
        poly = PurePoly.new(poly, Dummy('x'))

    if not args.get('polys', False):
        return poly.as_expr()
    else:
        return poly

@cythonized("n,i")
def dup_legendre(n, K):
    """Low-level implementation of Legendre polynomials. """
    seq = [[K.one], [K.one, K.zero]]

    for i in range(2, n+1):
        a = dup_mul_ground(dup_lshift(seq[-1], 1, K), K(2*i-1, i), K)
        b = dup_mul_ground(seq[-2], K(i-1, i), K)

        seq.append(dup_sub(a, b, K))

    return seq[n]

def legendre_poly(n, x=None, **args):
    """Generates Legendre polynomial of degree `n` in `x`. """
    if n < 0:
        raise ValueError("can't generate Legendre polynomial of degree %s" % n)

    poly = DMP(dup_legendre(int(n), QQ), QQ)

    if x is not None:
        poly = Poly.new(poly, x)
    else:
        poly = PurePoly.new(poly, Dummy('x'))

    if not args.get('polys', False):
        return poly.as_expr()
    else:
        return poly

@cythonized("n,i")
def dup_laguerre(n, alpha, K):
    """Low-level implementation of Laguerre polynomials. """
    seq = [[K.zero], [K.one]]

    for i in range(1, n+1):
        a = dup_mul(seq[-1], [-K.one/i, alpha/i + K(2*i-1)/i], K)
        b = dup_mul_ground(seq[-2], alpha/i + K(i-1)/i, K)

        seq.append(dup_sub(a, b, K))

    return seq[-1]

def laguerre_poly(n, x=None, alpha=None, **args):
    """Generates Laguerre polynomial of degree `n` in `x`. """
    if n < 0:
        raise ValueError("can't generate Laguerre polynomial of degree %s" % n)

    if alpha is not None:
        K, alpha = construct_domain(alpha, field=True) # XXX: ground_field=True
    else:
        K, alpha = QQ, QQ(0)

    poly = DMP(dup_laguerre(int(n), alpha, K), K)

    if x is not None:
        poly = Poly.new(poly, x)
    else:
        poly = PurePoly.new(poly, Dummy('x'))

    if not args.get('polys', False):
        return poly.as_expr()
    else:
        return poly

@cythonized("n,i")
def dup_spherical_bessel_fn(n, K):
    """ Low-level implementation of fn(n, x) """
    seq = [[K.one], [K.one, K.zero]]

    for i in range(2, n+1):
        a = dup_mul_ground(dup_lshift(seq[-1], 1, K), K(2*i-1), K)
        seq.append(dup_sub(a, seq[-2], K))

    return dup_lshift(seq[n], 1, K)

@cythonized("n,i")
def dup_spherical_bessel_fn_minus(n, K):
    """ Low-level implementation of fn(-n, x) """
    seq = [[K.one, K.zero], [K.zero]]

    for i in range(2, n+1):
        a = dup_mul_ground(dup_lshift(seq[-1], 1, K), K(3 - 2*i), K)
        seq.append(dup_sub(a, seq[-2], K))

    return seq[n]

def spherical_bessel_fn(n, x=None, **args):
    """
    Coefficients for the spherical Bessel functions.

    Those are only needed in the jn() function.

    The coefficients are calculated from:

    fn(0, z) = 1/z
    fn(1, z) = 1/z**2
    fn(n-1, z) + fn(n+1, z) == (2*n+1)/z * fn(n, z)

    Examples:

    >>> from sympy.polys.orthopolys import spherical_bessel_fn as fn
    >>> from sympy import Symbol
    >>> z = Symbol("z")
    >>> fn(1, z)
    z**(-2)
    >>> fn(2, z)
    -1/z + 3/z**3
    >>> fn(3, z)
    -6/z**2 + 15/z**4
    >>> fn(4, z)
    1/z - 45/z**3 + 105/z**5

    """
    from sympy import sympify

    if n < 0:
        dup = dup_spherical_bessel_fn_minus(-int(n), ZZ)
    else:
        dup = dup_spherical_bessel_fn(int(n), ZZ)

    poly = DMP(dup, ZZ)

    if x is not None:
        poly = Poly.new(poly, 1/x)
    else:
        poly = PurePoly.new(poly, 1/Dummy('x'))

    if not args.get('polys', False):
        return poly.as_expr()
    else:
        return poly
