#!/usr/bin/env python3
from timeit import default_timer as clock
from random import random
from sympy import Symbol, I, sqrt, Integer, factorial, pi, exp, pprint, \
    simplify, sin, sympify, factor

x = Symbol("x")
y = Symbol("y")
z = Symbol("z")

def bench_R1():
    "real(f(f(f(f(f(f(f(f(f(f(i/2)))))))))))"
    def f(z): return sqrt(Integer(1)/3)*z**2 + I/3
    e = f(f(f(f(f(f(f(f(f(f(I/2)))))))))).as_real_imag()[0]

def bench_R2():
    "Hermite polynomial hermite(15, y)"
    def hermite(n, y):
        if n == 1: return 2*y
        if n == 0: return 1
        return (2*y*hermite(n-1,y) - 2*(n-1)*hermite(n-2,y)).expand()

    #def phi(n, y):
    #  return 1/(sqrt(2**n*factorial(n))*pi**(Integer(1)/4))*exp(-y**2/2)* \
    #            hermite(n,y)

    a = hermite(15, y)

def bench_R3():
    "a = [bool(f==f) for _ in range(10)]"
    f = x+y+z
    a = [bool(f==f) for _ in range(10)]

def bench_R4():
    # we don't have Tuples
    pass

def bench_R5():
    "blowup(L, 8); L=uniq(L)"
    def blowup(L,n):
        for i in range(n):
            L.append( (L[i] + L[i+1]) * L[i+2] )
    def uniq(x):
        v = list(set(x))
        v.sort()
        return v
    L = [x, y, z]
    blowup(L, 8)
    L = uniq(L)

def bench_R6():
    "sum(simplify((x+sin(i))/x+(x-sin(i))/x) for i in xrange(100))"
    s = sum(simplify((x+sin(i))/x+(x-sin(i))/x) for i in range(100))

def bench_R7():
    "[f.subs(x, random()) for _ in xrange(10**4)]"
    f = x**24+34*x**12+45*x**3+9*x**18+34*x**10+32*x**21
    a = [f.subs(x, random()) for _ in range(10**4)]

def bench_R8():
    "right(x^2,0,5,10^4)"
    def right(f,a,b,n):
        a = sympify(a)
        b = sympify(b)
        n = sympify(n)
        x = f.atoms(Symbol).pop()
        Deltax = (b-a)/n; c=a; est=0
        for i in range(n):
            c += Deltax
            est += f.subs(x, c)
        return est*Deltax

    a = right(x**2,0,5,10**4)

def _bench_R9():
    "factor(x^20 - pi^5*y^20)"
    factor(x**20 - pi**5*y**20)

def bench_R10():
    "v = [-pi,-pi+1/10..,pi]"
    def srange(min, max, step):
        v = [min]
        while (max-v[-1]).evalf() > 0:
            v.append(v[-1]+step)
        return v[:-1]
    v = srange(-pi, pi, sympify(1)/10)

def bench_R11():
    "a = [random() + random()*I for w in [0..1000]]"
    a = [random() + random()*I for w in range(1000)]
    a.sort()


def bench_S1():
    "e=(x+y+z+1)**7;f=e*(e+1);f.expand()"
    e = (x+y+z+1)**7
    f = e*(e+1)
    f = f.expand()


if __name__ == '__main__':
    benchmarks = [
            bench_R1,
            bench_R2,
            bench_R3,
            bench_R5,
            bench_R6,
            bench_R7,
            bench_R8,
            #_bench_R9,
            bench_R10,
            bench_R11,
            #bench_S1,
            ]

    report = []
    for b in benchmarks:
        t = clock()
        b()
        t = clock()-t
        print("%s%65s: %f" % (b.__name__, b.__doc__, t))
