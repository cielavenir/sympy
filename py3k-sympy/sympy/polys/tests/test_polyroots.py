"""Tests for algorithms for computing symbolic roots of polynomials. """

from sympy import (S, symbols, Symbol, Wild, Integer, Rational, sqrt,
    powsimp, Lambda, sin, cos, pi, I)
from sympy.utilities.pytest import raises

from sympy.polys import Poly, cyclotomic_poly

from sympy.polys.polyroots import (root_factors, roots_linear,
    roots_quadratic, roots_cubic, roots_quartic, roots_cyclotomic,
    roots_binomial, roots_rational, preprocess_roots, roots)

a, b, c, d, e, t, x, y, z = symbols('a,b,c,d,e,t,x,y,z')

def test_roots_linear():
    assert roots_linear(Poly(2*x+1, x)) == [-Rational(1, 2)]

def test_roots_quadratic():
    assert roots_quadratic(Poly(2*x**2, x)) == [0, 0]
    assert roots_quadratic(Poly(2*x**2 + 3*x, x)) == [-Rational(3, 2), 0]
    assert roots_quadratic(Poly(2*x**2 + 3, x)) == [-I*sqrt(6)/2, I*sqrt(6)/2]
    assert roots_quadratic(Poly(2*x**2 + 4*x+3, x)) == [-1 - I*sqrt(2)/2, -1 + I*sqrt(2)/2]

    f = x**2 + (2*a*e + 2*c*e)/(a - c)*x + (d - b + a*e**2 - c*e**2)/(a - c)

    assert roots_quadratic(Poly(f, x)) == \
        [-e*(a + c)/(a - c) - ((a*b + c*d - a*d - b*c + 4*a*c*e**2)/(a - c)**2)**S.Half,
         -e*(a + c)/(a - c) + ((a*b + c*d - a*d - b*c + 4*a*c*e**2)/(a - c)**2)**S.Half]

def test_roots_cubic():
    assert roots_cubic(Poly(2*x**3, x)) == [0, 0, 0]
    assert roots_cubic(Poly(x**3-3*x**2+3*x-1, x)) == [1, 1, 1]

    assert roots_cubic(Poly(x**3+1, x)) == \
        [-1, S.Half - I*sqrt(3)/2, S.Half + I*sqrt(3)/2]

def test_roots_quartic():
    assert roots_quartic(Poly(x**4, x)) == [0, 0, 0, 0]
    assert roots_quartic(Poly(x**4 + x**3, x)) in [
        [-1,0,0,0],
        [0,-1,0,0],
        [0,0,-1,0],
        [0,0,0,-1]
    ]
    assert roots_quartic(Poly(x**4 - x**3, x)) in [
        [1,0,0,0],
        [0,1,0,0],
        [0,0,1,0],
        [0,0,0,1]
    ]

    lhs = roots_quartic(Poly(x**4 + x, x))
    rhs = [S.Half + I*sqrt(3)/2, S.Half - I*sqrt(3)/2, S.Zero, -S.One]

    assert sorted(lhs, key=hash) == sorted(rhs, key=hash)

    # test of all branches of roots quartic
    for i, (a, b, c, d) in enumerate([(1, 2, 3, 0),
                                      (3, -7, -9, 9),
                                      (1, 2, 3, 4),
                                      (1, 2, 3, 4),
                                      (-7, -3, 3, -6),
                                      (-3, 5, -6, -4)]):
        if i == 2:
            c = -a*(a**2/S(8) - b/S(2))
        elif i == 3:
            d = a*(a*(3*a**2/S(256) - b/S(16)) + c/S(4))
        eq = x**4 + a*x**3 + b*x**2 + c*x + d
        ans = roots_quartic(Poly(eq, x))
        assert all([eq.subs(x, ai).n(chop=True) == 0 for ai in ans])

def test_roots_cyclotomic():
    assert roots_cyclotomic(cyclotomic_poly(1, x, polys=True)) == [1]
    assert roots_cyclotomic(cyclotomic_poly(2, x, polys=True)) == [-1]
    assert roots_cyclotomic(cyclotomic_poly(3, x, polys=True)) == [-S(1)/2 - I*3**(S(1)/2)/2, -S(1)/2 + I*3**(S(1)/2)/2]
    assert roots_cyclotomic(cyclotomic_poly(4, x, polys=True)) == [-I, I]
    assert roots_cyclotomic(cyclotomic_poly(6, x, polys=True)) == [S(1)/2 - I*3**(S(1)/2)/2, S(1)/2 + I*3**(S(1)/2)/2]

    assert roots_cyclotomic(cyclotomic_poly(7, x, polys=True)) == [
        -cos(pi/7)   - I*sin(pi/7),
        -cos(pi/7)   + I*sin(pi/7),
         cos(2*pi/7) - I*sin(2*pi/7),
         cos(2*pi/7) + I*sin(2*pi/7),
        -cos(3*pi/7) - I*sin(3*pi/7),
        -cos(3*pi/7) + I*sin(3*pi/7),
    ]

    assert roots_cyclotomic(cyclotomic_poly(8, x, polys=True)) == [
        -2**(S(1)/2)/2 - I*2**(S(1)/2)/2,
        -2**(S(1)/2)/2 + I*2**(S(1)/2)/2,
         2**(S(1)/2)/2 - I*2**(S(1)/2)/2,
         2**(S(1)/2)/2 + I*2**(S(1)/2)/2,
    ]

    assert roots_cyclotomic(cyclotomic_poly(12, x, polys=True)) == [
        -3**(S(1)/2)/2 - I/2,
        -3**(S(1)/2)/2 + I/2,
         3**(S(1)/2)/2 - I/2,
         3**(S(1)/2)/2 + I/2,
    ]

    assert roots_cyclotomic(cyclotomic_poly(1, x, polys=True), factor=True) == [1]
    assert roots_cyclotomic(cyclotomic_poly(2, x, polys=True), factor=True) == [-1]

    assert roots_cyclotomic(cyclotomic_poly(3, x, polys=True), factor=True) == \
        [-(-1)**(S(1)/3), -1 + (-1)**(S(1)/3)]
    assert roots_cyclotomic(cyclotomic_poly(4, x, polys=True), factor=True) == \
        [-I, I]
    assert roots_cyclotomic(cyclotomic_poly(5, x, polys=True), factor=True) == \
        [-(-1)**(S(1)/5), (-1)**(S(2)/5), -(-1)**(S(3)/5), -1 + (-1)**(S(1)/5) - (-1)**(S(2)/5) + (-1)**(S(3)/5)]
    assert roots_cyclotomic(cyclotomic_poly(6, x, polys=True), factor=True) == \
        [(-1)**(S(1)/3), 1 - (-1)**(S(1)/3)]

def test_roots_binomial():
    assert roots_binomial(Poly(5*x, x)) == [0]
    assert roots_binomial(Poly(5*x**4, x)) == [0, 0, 0, 0]
    assert roots_binomial(Poly(5*x+2, x)) == [-Rational(2, 5)]

    A = 10**Rational(3, 4)/10

    assert roots_binomial(Poly(5*x**4+2, x)) == \
        [-A - A*I, -A + A*I, A - A*I, A + A*I]

    a1 = Symbol('a1', nonnegative=True)
    b1 = Symbol('b1', nonnegative=True)

    r0 = roots_quadratic(Poly(a1*x**2 + b1, x))
    r1 = roots_binomial(Poly(a1*x**2 + b1, x))

    assert powsimp(r0[0]) == powsimp(r1[0])
    assert powsimp(r0[1]) == powsimp(r1[1])

def test_roots_rational():
    assert roots_rational(Poly(x**2-1, x)) == [-S.One, S.One]
    assert roots_rational(Poly(x**2-x, x)) == [S.Zero, S.One]

    assert roots_rational(Poly(x**2-x/2, x)) == [S.Zero]
    assert roots_rational(Poly(2*x**2-x, x)) == [S.Zero]

    assert roots_rational(Poly(t*x**2-x, x)) == []

def test_roots_preprocessing():
    f = a*y*x**2 + y - b

    coeff, poly = preprocess_roots(Poly(f, x))

    assert coeff == 1
    assert poly == Poly(a*y*x**2 + y - b, x)

    f = c**3*x**3 + c**2*x**2 + c*x + a

    coeff, poly = preprocess_roots(Poly(f, x))

    assert coeff == 1/c
    assert poly == Poly(x**3 + x**2 + x + a, x)

    f = c**3*x**3 + c**2*x**2 + a

    coeff, poly = preprocess_roots(Poly(f, x))

    assert coeff == 1/c
    assert poly == Poly(x**3 + x**2 + a, x)

    f = c**3*x**3 + c*x + a

    coeff, poly = preprocess_roots(Poly(f, x))

    assert coeff == 1/c
    assert poly == Poly(x**3 + x + a, x)

    f = c**3*x**3 + a

    coeff, poly = preprocess_roots(Poly(f, x))

    assert coeff == 1/c
    assert poly == Poly(x**3 + a, x)

    E, F, J, L = symbols("E,F,J,L")

    f = -21601054687500000000*E**8*J**8/L**16 + \
         508232812500000000*F*x*E**7*J**7/L**14 - \
         4269543750000000*E**6*F**2*J**6*x**2/L**12 + \
         16194716250000*E**5*F**3*J**5*x**3/L**10 - \
         27633173750*E**4*F**4*J**4*x**4/L**8 + \
         14840215*E**3*F**5*J**3*x**5/L**6 + \
         54794*E**2*F**6*J**2*x**6/(5*L**4) - \
         1153*E*J*F**7*x**7/(80*L**2) + \
         633*F**8*x**8/160000

    coeff, poly = preprocess_roots(Poly(f, x))

    assert coeff == 20*E*J/(F*L**2)
    assert poly == 633*x**8 - 115300*x**7 + 4383520*x**6 + 296804300*x**5 - 27633173750*x**4 + \
        809735812500*x**3 - 10673859375000*x**2 + 63529101562500*x - 135006591796875

def test_roots():
    assert roots(1, x) == {}
    assert roots(x, x) == {S.Zero: 1}
    assert roots(x**9, x) == {S.Zero: 9}
    assert roots(((x-2)*(x+3)*(x-4)).expand(), x) == {-S(3): 1, S(2): 1, S(4): 1}

    assert roots(2*x+1, x) == {-S.Half: 1}
    assert roots((2*x+1)**2, x) == {-S.Half: 2}
    assert roots((2*x+1)**5, x) == {-S.Half: 5}
    assert roots((2*x+1)**10, x) == {-S.Half: 10}

    assert roots(x**4 - 1, x) == {I: 1, S.One: 1, -S.One: 1, -I: 1}
    assert roots((x**4 - 1)**2, x) == {I: 2, S.One: 2, -S.One: 2, -I: 2}

    assert roots(((2*x-3)**2).expand(), x) == { Rational(3,2): 2}
    assert roots(((2*x+3)**2).expand(), x) == {-Rational(3,2): 2}

    assert roots(((2*x-3)**3).expand(), x) == { Rational(3,2): 3}
    assert roots(((2*x+3)**3).expand(), x) == {-Rational(3,2): 3}

    assert roots(((2*x-3)**5).expand(), x) == { Rational(3,2): 5}
    assert roots(((2*x+3)**5).expand(), x) == {-Rational(3,2): 5}

    assert roots(((a*x-b)**5).expand(), x) == { b/a: 5}
    assert roots(((a*x+b)**5).expand(), x) == {-b/a: 5}

    assert roots(x**4-2*x**2+1, x) == {S.One: 2, -S.One: 2}

    assert roots(x**6-4*x**4+4*x**3-x**2, x) == \
        {S.One: 2, -1 - sqrt(2): 1, S.Zero: 2, -1 + sqrt(2): 1}

    assert roots(x**8-1, x) == {
         2**S.Half/2 + I*2**S.Half/2: 1,
         2**S.Half/2 - I*2**S.Half/2: 1,
        -2**S.Half/2 + I*2**S.Half/2: 1,
        -2**S.Half/2 - I*2**S.Half/2: 1,
        S.One: 1, -S.One: 1, I: 1, -I: 1
    }

    f = -2016*x**2 - 5616*x**3 - 2056*x**4 + 3324*x**5 + 2176*x**6 - 224*x**7 - 384*x**8 - 64*x**9

    assert roots(f) == {S(0): 2, -S(2): 2, S(2): 1, -S(7)/2: 1, -S(3)/2: 1, -S(1)/2: 1, S(3)/2: 1}

    assert roots((a+b+c)*x - (a+b+c+d), x) == {(a+b+c+d)/(a+b+c): 1}

    assert roots(x**3+x**2-x+1, x, cubics=False) == {}
    assert roots(((x-2)*(x+3)*(x-4)).expand(), x, cubics=False) == {-S(3): 1, S(2): 1, S(4): 1}
    assert roots(((x-2)*(x+3)*(x-4)*(x-5)).expand(), x, cubics=False) == \
            {-S(3): 1, S(2): 1, S(4): 1, S(5): 1}
    assert roots(x**3 + 2*x**2 + 4*x + 8, x) == {-S(2): 1, -2*I: 1, 2*I: 1}
    assert roots(x**3 + 2*x**2 + 4*x + 8, x, cubics=True) == \
                {-2*I: 1, 2*I: 1, -S(2): 1}
    assert roots((x**2 - x)*(x**3 + 2*x**2 + 4*x + 8), x ) == \
                {S(1): 1, S(0): 1, -S(2): 1, -2*I: 1, 2*I: 1}

    r1_2, r1_3, r1_9, r4_9, r19_27 = [ Rational(*r) \
        for r in ((1,2), (1,3), (1,9), (4,9), (19,27)) ]

    U = -r1_2 - r1_2*I*3**r1_2
    V = -r1_2 + r1_2*I*3**r1_2
    W = (r19_27 + r1_9*33**r1_2)**r1_3

    assert roots(x**3+x**2-x+1, x, cubics=True) == {
        -r1_3 - U*W - r4_9*(U*W)**(-1): 1,
        -r1_3 - V*W - r4_9*(V*W)**(-1): 1,
        -r1_3 -   W - r4_9*(  W)**(-1): 1,
    }

    f = (x**2+2*x+3).subs(x, 2*x**2 + 3*x).subs(x, 5*x-4)

    r1_2, r13_20, r1_100 = [ Rational(*r) \
        for r in ((1,2), (13,20), (1,100)) ]

    assert roots(f, x) == {
        r13_20 + r1_100*(25 - 200*I*2**r1_2)**r1_2: 1,
        r13_20 - r1_100*(25 - 200*I*2**r1_2)**r1_2: 1,
        r13_20 + r1_100*(25 + 200*I*2**r1_2)**r1_2: 1,
        r13_20 - r1_100*(25 + 200*I*2**r1_2)**r1_2: 1,
    }

    f = x**4 + x**3 + x**2 + x + 1

    r1_4, r1_8, r5_8 = [ Rational(*r) for r in ((1,4), (1,8), (5,8)) ]

    assert roots(f, x) == {
        -r1_4 + r1_4*5**r1_2 + I*(r5_8 + r1_8*5**r1_2)**r1_2: 1,
        -r1_4 + r1_4*5**r1_2 - I*(r5_8 + r1_8*5**r1_2)**r1_2: 1,
        -r1_4 - r1_4*5**r1_2 + I*(r5_8 - r1_8*5**r1_2)**r1_2: 1,
        -r1_4 - r1_4*5**r1_2 - I*(r5_8 - r1_8*5**r1_2)**r1_2: 1,
    }

    f = z**3 + (-2 - y)*z**2 + (1 + 2*y - 2*x**2)*z - y + 2*x**2

    assert roots(f, z) == {
        S.One: 1,
        S.Half + S.Half*y + S.Half*(1 - 2*y + y**2 + 8*x**2)**S.Half: 1,
        S.Half + S.Half*y - S.Half*(1 - 2*y + y**2 + 8*x**2)**S.Half: 1,
    }

    assert roots(a*b*c*x**3 + 2*x**2 + 4*x + 8, x, cubics=False) == {}
    assert roots(a*b*c*x**3 + 2*x**2 + 4*x + 8, x, cubics=True) != {}

    assert roots(x**4-1, x, filter='Z') == {S.One: 1, -S.One: 1}
    assert roots(x**4-1, x, filter='I') == {I: 1, -I: 1}

    assert roots((x-1)*(x+1), x) == {S.One: 1, -S.One: 1}
    assert roots((x-1)*(x+1), x, predicate=lambda r: r.is_positive) == {S.One: 1}

    assert roots(x**4-1, x, filter='Z', multiple=True) == [-S.One, S.One]
    assert roots(x**4-1, x, filter='I', multiple=True) == [-I, I]

    assert roots(x**3, x, multiple=True) == [S.Zero, S.Zero, S.Zero]
    assert roots(1234, x, multiple=True) == []

    f = x**6 - x**5 + x**4 - x**3 + x**2 - x + 1

    assert roots(f) == {
        -I*sin(pi/7)   + cos(pi/7):   1,
        -I*sin(2*pi/7) - cos(2*pi/7): 1,
        -I*sin(3*pi/7) + cos(3*pi/7): 1,
         I*sin(pi/7)   + cos(pi/7):   1,
         I*sin(2*pi/7) - cos(2*pi/7): 1,
         I*sin(3*pi/7) + cos(3*pi/7): 1,
    }

    g = ((x**2 + 1)*f**2).expand()

    assert roots(g) == {
        -I*sin(pi/7)   + cos(pi/7):   2,
        -I*sin(2*pi/7) - cos(2*pi/7): 2,
        -I*sin(3*pi/7) + cos(3*pi/7): 2,
         I*sin(pi/7)   + cos(pi/7):   2,
         I*sin(2*pi/7) - cos(2*pi/7): 2,
         I*sin(3*pi/7) + cos(3*pi/7): 2,
        -I: 1, I: 1,
    }

def test_roots2():
    """Just test that calculating these roots does not hang
    (final result is not checked)
    """
    a, b, c, d, x = symbols("a,b,c,d,x")

    f1 = x**2*c + (a/b) + x*c*d - a
    f2 = x**2*(a + b*(c-d)*a) + x*a*b*c/(b*d-d) + (a*d-c/d)

    assert list(roots(f1, x).values()) == [1, 1]
    assert list(roots(f2, x).values()) == [1, 1]

    (zz, yy, xx, zy, zx, yx, k) = symbols("zz,yy,xx,zy,zx,yx,k")

    e1 = (zz-k)*(yy-k)*(xx-k) + zy*yx*zx + zx-zy-yx
    e2 = (zz-k)*yx*yx + zx*(yy-k)*zx + zy*zy*(xx-k)

    assert list(roots(e1 - e2, k).values()) == [1, 1, 1]

def test_roots_inexact():
    R1 = sorted([ r.evalf() for r in roots(x**2 + x + 1,   x) ])
    R2 = sorted([ r         for r in roots(x**2 + x + 1.0, x) ])

    for r1, r2 in zip(R1, R2):
        assert abs(r1 - r2) < 1e-12

    f = x**4 + 3.0*sqrt(2.0)*x**3 - (78.0 + 24.0*sqrt(3.0))*x**2 + 144.0*(2*sqrt(3.0) + 9.0)

    R1 = sorted(roots(f, multiple=True))
    R2 = sorted([-12.7530479110482, -3.85012393732929, 4.89897948556636, 7.46155167569183])

    for r1, r2 in zip(R1, R2):
        assert abs(r1 - r2) < 1e-10

def test_roots_preprocessed():
    E, F, J, L = symbols("E,F,J,L")

    f = -21601054687500000000*E**8*J**8/L**16 + \
         508232812500000000*F*x*E**7*J**7/L**14 - \
         4269543750000000*E**6*F**2*J**6*x**2/L**12 + \
         16194716250000*E**5*F**3*J**5*x**3/L**10 - \
         27633173750*E**4*F**4*J**4*x**4/L**8 + \
         14840215*E**3*F**5*J**3*x**5/L**6 + \
         54794*E**2*F**6*J**2*x**6/(5*L**4) - \
         1153*E*J*F**7*x**7/(80*L**2) + \
         633*F**8*x**8/160000

    assert roots(f, x) == {}

    R1 = roots(f.evalf(), x, multiple=True)
    R2 = [-1304.88375606366, 97.1168816800648, 186.946430171876, 245.526792947065,
           503.441004174773, 791.549343830097, 1273.16678129348, 1850.10650616851]

    w = Wild('w')
    p = w*E*J/(F*L**2)

    assert len(R1) == len(R2)

    for r1, r2 in zip(R1, R2):
        match = r1.match(p)
        assert match is not None and abs(match[w] - r2) < 1e-10

def test_root_factors():
    assert root_factors(Poly(1, x)) == [Poly(1, x)]
    assert root_factors(Poly(x, x)) == [Poly(x, x)]

    assert root_factors(Poly(x**2-1, x)) == [Poly(x-1, x), Poly(x+1, x)]

    factors = root_factors(Poly((x**4 - 1)**2, x))

    assert len(factors) == 8
    assert set(factors) == set([Poly(x-I, x), Poly(x-1, x), Poly(x+1, x), Poly(x+I, x)])

    assert root_factors(Poly(x**4-1, x), filter='Z') == \
        [Poly(x-1, x), Poly(x+1, x), Poly(x**2+1, x)]

    assert root_factors(8*x**2 + 12*x**4 + 6*x**6 + x**8, x, filter='Q') == \
        [x, x, x**6 + 6*x**4 + 12*x**2 + 8]
