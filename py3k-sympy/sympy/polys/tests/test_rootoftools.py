"""Tests for the implementation of RootOf class and related tools. """

from sympy.polys.polytools import Poly
from sympy.polys.rootoftools import RootOf, RootSum

from sympy.polys.polyerrors import (
    MultivariatePolynomialError,
    GeneratorsNeeded,
    PolynomialError,
)

from sympy import (
    S, symbols, sqrt, I, Rational, Float, Lambda, log, exp, tan,
)

from sympy.utilities.pytest import raises

from sympy.abc import a, b, c, d, x, y, z, r

def test_RootOf___new__():
    assert RootOf(x, 0) == 0
    assert RootOf(x,-1) == 0

    assert RootOf(x, S.Zero) == 0

    assert RootOf(x - 1, 0) == 1
    assert RootOf(x - 1,-1) == 1

    assert RootOf(x + 1, 0) ==-1
    assert RootOf(x + 1,-1) ==-1

    assert RootOf(x**2 + 2*x + 3, 0) == -1 - I*sqrt(2)
    assert RootOf(x**2 + 2*x + 3, 1) == -1 + I*sqrt(2)
    assert RootOf(x**2 + 2*x + 3,-1) == -1 + I*sqrt(2)
    assert RootOf(x**2 + 2*x + 3,-2) == -1 - I*sqrt(2)

    r = RootOf(x**2 + 2*x + 3, 0, radicals=False)
    assert isinstance(r, RootOf) == True

    r = RootOf(x**2 + 2*x + 3, 1, radicals=False)
    assert isinstance(r, RootOf) == True

    r = RootOf(x**2 + 2*x + 3,-1, radicals=False)
    assert isinstance(r, RootOf) == True

    r = RootOf(x**2 + 2*x + 3,-2, radicals=False)
    assert isinstance(r, RootOf) == True

    assert RootOf((x - 1)*(x + 1), 0, radicals=False) ==-1
    assert RootOf((x - 1)*(x + 1), 1, radicals=False) == 1
    assert RootOf((x - 1)*(x + 1),-1, radicals=False) == 1
    assert RootOf((x - 1)*(x + 1),-2, radicals=False) ==-1

    assert RootOf((x - 1)*(x + 1), 0, radicals=True) ==-1
    assert RootOf((x - 1)*(x + 1), 1, radicals=True) == 1
    assert RootOf((x - 1)*(x + 1),-1, radicals=True) == 1
    assert RootOf((x - 1)*(x + 1),-2, radicals=True) ==-1

    assert RootOf((x - 1)*(x**3 + x + 3), 0) == RootOf(x**3 + x + 3, 0)
    assert RootOf((x - 1)*(x**3 + x + 3), 1) == 1
    assert RootOf((x - 1)*(x**3 + x + 3), 2) == RootOf(x**3 + x + 3, 1)
    assert RootOf((x - 1)*(x**3 + x + 3), 3) == RootOf(x**3 + x + 3, 2)
    assert RootOf((x - 1)*(x**3 + x + 3),-1) == RootOf(x**3 + x + 3, 2)
    assert RootOf((x - 1)*(x**3 + x + 3),-2) == RootOf(x**3 + x + 3, 1)
    assert RootOf((x - 1)*(x**3 + x + 3),-3) == 1
    assert RootOf((x - 1)*(x**3 + x + 3),-4) == RootOf(x**3 + x + 3, 0)

    assert RootOf(x**4 + 3*x**3, 0) ==-3
    assert RootOf(x**4 + 3*x**3, 1) == 0
    assert RootOf(x**4 + 3*x**3, 2) == 0
    assert RootOf(x**4 + 3*x**3, 3) == 0

    raises(GeneratorsNeeded, "RootOf(0, 0)")
    raises(GeneratorsNeeded, "RootOf(1, 0)")

    raises(PolynomialError, "RootOf(Poly(0, x), 0)")
    raises(PolynomialError, "RootOf(Poly(1, x), 0)")

    raises(PolynomialError, "RootOf(x - y, 0)")

    raises(NotImplementedError, "RootOf(x**3 - x + sqrt(2), 0)")
    raises(NotImplementedError, "RootOf(x**3 - x + I, 0)")

    raises(IndexError, "RootOf(x**2 - 1,-4)")
    raises(IndexError, "RootOf(x**2 - 1,-3)")
    raises(IndexError, "RootOf(x**2 - 1, 2)")
    raises(IndexError, "RootOf(x**2 - 1, 3)")

    assert RootOf(Poly(x - y, x), 0) == y

    assert RootOf(Poly(x**2 - y, x), 0) == -sqrt(y)
    assert RootOf(Poly(x**2 - y, x), 1) ==  sqrt(y)

    assert RootOf(Poly(x**3 - y, x), 0) == y**Rational(1,3)

    assert RootOf(y*x**3 + y*x + 2*y, x, 0) == -1
    raises(NotImplementedError, "RootOf(x**3 + x + 2*y, x, 0)")

    assert RootOf(x**3 + x + 1, 0).is_commutative == True

def test_RootOf_free_symbols():
    assert RootOf(x**3 + x + 3, 0).free_symbols == set()

def test_RootOf___eq__():
    assert (RootOf(x**3 + x + 3, 0) == RootOf(x**3 + x + 3, 0)) == True
    assert (RootOf(x**3 + x + 3, 0) == RootOf(x**3 + x + 3, 1)) == False
    assert (RootOf(x**3 + x + 3, 1) == RootOf(x**3 + x + 3, 1)) == True
    assert (RootOf(x**3 + x + 3, 1) == RootOf(x**3 + x + 3, 2)) == False
    assert (RootOf(x**3 + x + 3, 2) == RootOf(x**3 + x + 3, 2)) == True

    assert (RootOf(x**3 + x + 3, 0) == RootOf(y**3 + y + 3, 0)) == True
    assert (RootOf(x**3 + x + 3, 0) == RootOf(y**3 + y + 3, 1)) == False
    assert (RootOf(x**3 + x + 3, 1) == RootOf(y**3 + y + 3, 1)) == True
    assert (RootOf(x**3 + x + 3, 1) == RootOf(y**3 + y + 3, 2)) == False
    assert (RootOf(x**3 + x + 3, 2) == RootOf(y**3 + y + 3, 2)) == True

def test_RootOf_is_real():
    assert RootOf(x**3 + x + 3, 0).is_real == True
    assert RootOf(x**3 + x + 3, 1).is_real == False
    assert RootOf(x**3 + x + 3, 2).is_real == False

def test_RootOf_is_complex():
    assert RootOf(x**3 + x + 3, 0).is_complex == False
    assert RootOf(x**3 + x + 3, 1).is_complex == True
    assert RootOf(x**3 + x + 3, 2).is_complex == True

def test_RootOf_subs():
    assert RootOf(x**3 + x + 1, 0).subs(x, y) == RootOf(y**3 + y + 1, 0)

def test_RootOf_diff():
    assert RootOf(x**3 + x + 1, 0).diff(x) == 0
    assert RootOf(x**3 + x + 1, 0).diff(y) == 0

def test_RootOf_evalf():
    real = RootOf(x**3 + x + 3, 0).evalf(n=20)

    assert real.epsilon_eq(Float("-1.2134116627622296341"))

    re, im = RootOf(x**3 + x + 3, 1).evalf(n=20).as_real_imag()

    assert re.epsilon_eq( Float("0.60670583138111481707"))
    assert im.epsilon_eq(-Float("1.45061224918844152650"))

    re, im = RootOf(x**3 + x + 3, 2).evalf(n=20).as_real_imag()

    assert re.epsilon_eq(Float("0.60670583138111481707"))
    assert im.epsilon_eq(Float("1.45061224918844152650"))

def test_RootOf_real_roots():
    assert Poly(x**5 + x + 1).real_roots() == [RootOf(x**3 - x**2 + 1, 0)]
    assert Poly(x**5 + x + 1).real_roots(radicals=False) == [RootOf(x**3 - x**2 + 1, 0)]

def test_RootOf_all_roots():
    assert Poly(x**5 + x + 1).all_roots() == [
        RootOf(x**3 - x**2 + 1, 0),
        -S(1)/2 - 3**(S(1)/2)*I/2,
        -S(1)/2 + 3**(S(1)/2)*I/2,
        RootOf(x**3 - x**2 + 1, 1),
        RootOf(x**3 - x**2 + 1, 2),
    ]

    assert Poly(x**5 + x + 1).all_roots(radicals=False) == [
        RootOf(x**3 - x**2 + 1, 0),
        RootOf(x**2 + x + 1, 0, radicals=False),
        RootOf(x**2 + x + 1, 1, radicals=False),
        RootOf(x**3 - x**2 + 1, 1),
        RootOf(x**3 - x**2 + 1, 2),
    ]

def test_RootSum___new__():
    f = x**3 + x + 3

    g = Lambda(r, log(r*x))
    s = RootSum(f, g)

    rootofs = sum(log(RootOf(f, i)*x) for i in (0, 1, 2))

    assert isinstance(s, RootSum) == True
    assert s.doit() == rootofs

    assert RootSum(f**2, g) == 2*RootSum(f, g)
    assert RootSum(f**2, g).doit() == 2*rootofs

    assert RootSum((x - 7)*f**3, g) == log(7*x) + 3*RootSum(f, g)
    assert RootSum((x - 7)*f**3, g).doit() == log(7*x) + 3*rootofs
    # Issue 2472
    assert hash(RootSum((x - 7)*f**3, g)) == hash(log(7*x) + 3*RootSum(f, g))

    raises(MultivariatePolynomialError, "RootSum(x**3 + x + y)")
    raises(ValueError, "RootSum(x**2 + 3, lambda x: x)")

    assert RootSum(f, exp) == RootSum(f, Lambda(x, exp(x)))
    assert RootSum(f, log) == RootSum(f, Lambda(x, log(x)))

    assert isinstance(RootSum(f, auto=False), RootSum) == True

    assert RootSum(f) == 0
    assert RootSum(f, Lambda(x, x)) == 0
    assert RootSum(f, Lambda(x, x**2)) == -2

    assert RootSum(f, Lambda(x, 1)) == 3
    assert RootSum(f, Lambda(x, 2)) == 6

    assert RootSum(f, auto=False).is_commutative == True

    assert RootSum(f, Lambda(x, 1/(x + x**2))) == S(11)/3
    assert RootSum(f, Lambda(x, y/(x + x**2))) == S(11)/3*y

    assert RootSum(x**2 - 1, Lambda(x, 3*x**2), x) == 6
    assert RootSum(x**2 - y, Lambda(x, 3*x**2), x) == 6*y

    assert RootSum(x**2 - 1, Lambda(x, z*x**2), x) == 2*z
    assert RootSum(x**2 - y, Lambda(x, z*x**2), x) == 2*z*y

    assert RootSum(x**2 - 1, Lambda(x, exp(x)), quadratic=True) == exp(-1) + exp(1)

    assert RootSum(x**3 + a*x + a**3, tan, x) == RootSum(x**3 + x + 1, Lambda(x, tan(a*x)))
    assert RootSum(a**3*x**3 + a*x + 1, tan, x) == RootSum(x**3 + x + 1, Lambda(x, tan(x/a)))

def test_RootSum_free_symbols():
    assert RootSum(x**3 + x + 3, Lambda(r, exp(r))).free_symbols == set()
    assert RootSum(x**3 + x + 3, Lambda(r, exp(a*r))).free_symbols == set([a])
    assert RootSum(x**3 + x + y, Lambda(r, exp(a*r)), x).free_symbols == set([a, y])

def test_RootSum___eq__():
    f = Lambda(x, exp(x))

    assert (RootSum(x**3 + x + 1, f) == RootSum(x**3 + x + 1, f)) == True
    assert (RootSum(x**3 + x + 1, f) == RootSum(y**3 + y + 1, f)) == True

    assert (RootSum(x**3 + x + 1, f) == RootSum(x**3 + x + 2, f)) == False
    assert (RootSum(x**3 + x + 1, f) == RootSum(y**3 + y + 2, f)) == False

def test_RootSum_diff():
    f = x**3 + x + 3

    g = Lambda(r,   exp(r*x))
    h = Lambda(r, r*exp(r*x))

    assert RootSum(f, g).diff(x) == RootSum(f, h)

def test_RootSum_subs():
    f = x**3 + x + 3
    g = Lambda(r, exp(r*x))

    F = y**3 + y + 3
    G = Lambda(r, exp(r*y))

    assert RootSum(f, g).subs(y, 1) == RootSum(f, g)
    assert RootSum(f, g).subs(x, y) == RootSum(F, G)

def test_RootSum_rational():
    assert RootSum(z**5 - z + 1, Lambda(z, z/(x - z))) == (4*x - 5)/(x**5 - x + 1)

    f = 161*z**3 + 115*z**2 + 19*z + 1
    g = Lambda(z, z*log(-3381*z**4/4 - 3381*z**3/4 - 625*z**2/2 - 125*z/2 - 5 + exp(x)))

    assert RootSum(f, g).diff(x) == -((5*exp(2*x) - 6*exp(x) + 4)*exp(x)/(exp(3*x) - exp(2*x) + 1))/7

def test_RootSum_independent():
    f = (x**3 - a)**2*(x**4 - b)**3

    g = Lambda(x, 5*tan(x) + 7)
    h = Lambda(x, tan(x))

    r0 = RootSum(x**3 - a, h, x)
    r1 = RootSum(x**4 - b, h, x)

    assert RootSum(f, g, x).as_ordered_terms() == [10*r0, 15*r1, 126]
