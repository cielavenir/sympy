# This testfile tests SymPy <-> NumPy compatibility

# Don't test any SymPy features here. Just pure interaction with NumPy.
# Always write regular SymPy tests for anything, that can be tested in pure
# Python (without numpy). Here we test everything, that a user may need when
# using SymPy with NumPy



from sympy.external import import_module

numpy = import_module('numpy')
if numpy:
    array, matrix, ndarray = numpy.array, numpy.matrix, numpy.ndarray
else:
    #py.test will not execute any tests now
    disabled = True


from sympy import (Rational, Symbol, list2numpy, sin, Float, Matrix, lambdify,
        symarray, symbols, Integer)
import sympy

from sympy import mpmath

# first, systematically check, that all operations are implemented and don't
# raise and exception

def test_systematic_basic():
    def s(sympy_object, numpy_array):
        x = sympy_object + numpy_array
        x = numpy_array + sympy_object
        x = sympy_object - numpy_array
        x = numpy_array - sympy_object
        x = sympy_object * numpy_array
        x = numpy_array * sympy_object
        x = sympy_object / numpy_array
        x = numpy_array / sympy_object
        x = sympy_object ** numpy_array
        x = numpy_array ** sympy_object
    x = Symbol("x")
    y = Symbol("y")
    sympy_objs = [
            Rational(2, 3),
            Float("1.3"),
            x,
            y,
            pow(x,y)*y,
            Integer(5),
            Float(5.5),
            ]
    numpy_objs = [
            array([1]),
            array([3, 8, -1]),
            array([x, x**2, Rational(5)]),
            array([x/y*sin(y), 5, Rational(5)]),
            ]
    for x in sympy_objs:
        for y in numpy_objs:
            s(x,y)


# now some random tests, that test particular problems and that also
# check that the results of the operations are correct

def test_basics():
    one = Rational(1)
    zero = Rational(0)
    x = Symbol("x")
    assert array(1) == array(one)
    assert array([one]) == array([one])
    assert array([x]) == array([x])
    assert array(x) == array(Symbol("x"))
    assert array(one+x) == array(1+x)

    X = array([one, zero, zero])
    assert (X == array([one, zero, zero])).all()
    assert (X == array([one, 0, 0])).all()

def test_arrays():
    one = Rational(1)
    zero = Rational(0)
    X = array([one, zero, zero])
    Y = one*X
    X = array([Symbol("a")+Rational(1,2)])
    Y = X+X
    assert Y == array([1+2*Symbol("a")])
    Y = Y + 1
    assert Y == array([2+2*Symbol("a")])
    Y = X-X
    assert Y == array([0])

def test_conversion1():
    x = Symbol("x")
    a = list2numpy([x**2, x])
    #looks like an array?
    assert isinstance(a, ndarray)
    assert a[0] == x**2
    assert a[1] == x
    assert len(a) == 2
    #yes, it's the array

def test_conversion2():
    x = Symbol("x")
    a = 2*list2numpy([x**2, x])
    b = list2numpy([2*x**2, 2*x])
    assert (a == b).all()

    one = Rational(1)
    zero = Rational(0)
    X = list2numpy([one, zero, zero])
    Y = one*X
    X = list2numpy([Symbol("a")+Rational(1,2)])
    Y = X+X
    assert Y == array([1+2*Symbol("a")])
    Y = Y + 1
    assert Y == array([2+2*Symbol("a")])
    Y = X-X
    assert Y == array([0])

def test_list2numpy():
    x = Symbol("x")
    assert (array([x**2, x]) == list2numpy([x**2, x])).all()

def test_Matrix1():
    x = Symbol("x")
    m = Matrix([[x, x**2], [5, 2/x]])
    assert (array(m.subs(x, 2)) == array([[2, 4],[5, 1]])).all()
    m = Matrix([[sin(x), x**2], [5, 2/x]])
    assert (array(m.subs(x, 2)) == array([[sin(2), 4],[5, 1]])).all()

def test_Matrix2():
    x = Symbol("x")
    m = Matrix([[x, x**2], [5, 2/x]])
    assert (matrix(m.subs(x, 2)) == matrix([[2, 4],[5, 1]])).all()
    m = Matrix([[sin(x), x**2], [5, 2/x]])
    assert (matrix(m.subs(x, 2)) == matrix([[sin(2), 4],[5, 1]])).all()

def test_Matrix3():
    x = Symbol("x")
    a = array([[2, 4],[5, 1]])
    assert Matrix(a) == Matrix([[2, 4], [5, 1]])
    assert Matrix(a) != Matrix([[2, 4], [5, 2]])
    a = array([[sin(2), 4], [5, 1]])
    assert Matrix(a) == Matrix([[sin(2), 4],[5, 1]])
    assert Matrix(a) != Matrix([[sin(0), 4],[5, 1]])

def test_Matrix4():
    x = Symbol("x")
    a = matrix([[2, 4],[5, 1]])
    assert Matrix(a) == Matrix([[2, 4], [5, 1]])
    assert Matrix(a) != Matrix([[2, 4], [5, 2]])
    a = matrix([[sin(2), 4], [5, 1]])
    assert Matrix(a) == Matrix([[sin(2), 4],[5, 1]])
    assert Matrix(a) != Matrix([[sin(0), 4],[5, 1]])

def test_Matrix_sum():
    x, y, z = Symbol('x'), Symbol('y'), Symbol('z')
    M = Matrix([[1,2,3],[x,y,x],[2*y,-50,z*x]])
    m = matrix([[2,3,4],[x,5,6],[x,y,z**2]])
    assert M+m == Matrix([[3,5,7],[2*x,y+5,x+6],[2*y+x,y-50,z*x+z**2]])
    assert m+M == Matrix([[3,5,7],[2*x,y+5,x+6],[2*y+x,y-50,z*x+z**2]])
    assert M+m == M.add(m)

def test_Matrix_mul():
    x, y, z = Symbol('x'), Symbol('y'), Symbol('z')
    M = Matrix([[1,2,3],[x,y,x]])
    m = matrix([[2,4],[x,6],[x,z**2]])
    assert M*m == Matrix([
                         [         2 + 5*x,        16 + 3*z**2],
                         [2*x + x*y + x**2, 4*x + 6*y + x*z**2],
                         ])

    assert m*M == Matrix([
                         [   2 + 4*x,      4 + 4*y,      6 + 4*x],
                         [       7*x,    2*x + 6*y,          9*x],
                         [x + x*z**2, 2*x + y*z**2, 3*x + x*z**2],
                         ])
    a = array([2])
    assert a[0] * M == 2 * M
    assert M * a[0] == 2 * M

def test_Matrix_array():
    class matarray(object):
        def __array__(self):
            from numpy import array
            return array([[1,2,3],[4,5,6],[7,8,9]])
    matarr = matarray()
    assert Matrix(matarr) == Matrix([[1,2,3],[4,5,6],[7,8,9]])

def test_issue629():
    x = Symbol("x")
    assert (Rational(1,2)*array([2*x, 0]) == array([x, 0])).all()
    assert (Rational(1,2) + array([2*x, 0]) == array([2*x + Rational(1,2), Rational(1,2)])).all()
    assert (Float("0.5")*array([2*x, 0]) == array([Float("1.0")*x, 0])).all()
    assert (Float("0.5") + array([2*x, 0]) == array([2*x + Float("0.5"), Float("0.5")])).all()

def test_lambdify():
    dps = mpmath.mp.dps
    try:
        mpmath.mp.dps = 16
        sin02 = mpmath.mpf("0.198669330795061215459412627")
        x = Symbol("x")
        f = lambdify(x, sin(x), "numpy")
        prec = 1e-15
        assert -prec < f(0.2) - sin02 < prec
        try:
            f(x) # if this succeeds, it can't be a numpy function
            assert False
        except AttributeError:
            pass
    finally:
        mpmath.mp.dps = dps

def test_lambdify_matrix():
    x = Symbol("x")
    f = lambdify(x, Matrix([[x, 2*x],[1, 2]]), "numpy")
    assert (f(1) == matrix([[1,2],[1,2]])).all()

def test_lambdify_matrix_multi_input():
    x,y,z = symbols('x,y,z')
    M=sympy.Matrix([[x**2, x*y, x*z],
                    [y*x, y**2, y*z],
                    [z*x, z*y, z**2]])
    f = lambdify((x,y,z), M, "numpy")

    xh,yh,zh = 1.0, 2.0, 3.0
    expected = matrix([[xh**2, xh*yh, xh*zh],
                       [yh*xh, yh**2, yh*zh],
                       [zh*xh, zh*yh, zh**2]])
    actual = f(xh,yh,zh)
    assert numpy.allclose(actual,expected)

def test_lambdify_matrix_vec_input():
    X=sympy.DeferredVector('X')
    M=Matrix([[X[0]**2, X[0]*X[1], X[0]*X[2]],
              [X[1]*X[0], X[1]**2, X[1]*X[2]],
              [X[2]*X[0], X[2]*X[1], X[2]**2]])
    f = lambdify(X, M, "numpy")

    Xh = array([1.0, 2.0, 3.0])
    expected = matrix([[Xh[0]**2, Xh[0]*Xh[1], Xh[0]*Xh[2]],
                       [Xh[1]*Xh[0], Xh[1]**2, Xh[1]*Xh[2]],
                       [Xh[2]*Xh[0], Xh[2]*Xh[1], Xh[2]**2]])
    actual = f(Xh)
    assert numpy.allclose(actual,expected)

def test_lambdify_transl():
    from sympy.utilities.lambdify import NUMPY_TRANSLATIONS
    for sym, mat in NUMPY_TRANSLATIONS.items():
        assert sym in sympy.__dict__
        assert mat in numpy.__dict__

def test_symarray():
    """Test creation of numpy arrays of sympy symbols."""

    import numpy as np
    import numpy.testing as npt

    syms = symbols('_0,_1,_2')
    s1 = symarray("", 3)
    s2 = symarray("", 3)
    npt.assert_array_equal (s1, np.array(syms, dtype=object))
    assert s1[0] is s2[0]

    a = symarray('a', 3)
    b = symarray('b', 3)
    assert not(a[0] is b[0])

    asyms = symbols('a_0,a_1,a_2')
    npt.assert_array_equal (a, np.array(asyms, dtype=object))

    # Multidimensional checks
    a2d = symarray('a', (2,3))
    assert a2d.shape == (2,3)
    a00, a12 = symbols('a_0_0,a_1_2')
    assert a2d[0,0] is a00
    assert a2d[1,2] is a12

    a3d = symarray('a', (2,3,2))
    assert a3d.shape == (2,3,2)
    a000, a120, a121 = symbols('a_0_0_0,a_1_2_0,a_1_2_1')
    assert a3d[0,0,0] is a000
    assert a3d[1,2,0] is a120
    assert a3d[1,2,1] is a121
