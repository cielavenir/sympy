"""This module implements tools for integrating rational functions. """

from sympy import S, Symbol, symbols, I, log, atan, \
    resultant, roots, collect, solve, RootSum, Lambda, cancel, Dummy

from sympy.polys import Poly, subresultants, resultant, ZZ

def ratint(f, x, **flags):
    """Performs indefinite integration of rational functions.

       Given a field K and a rational function f = p/q, where p and q
       are polynomials in K[x], returns a function g such that f = g'.

       >>> from sympy.integrals.rationaltools import ratint
       >>> from sympy.abc import x

       >>> ratint(36/(x**5 - 2*x**4 - 2*x**3 + 4*x**2 + x - 2), x)
       (12*x + 6)/(x**2 - 1) + 4*log(x - 2) - 4*log(x + 1)

       References
       ==========

       .. [Bro05] M. Bronstein, Symbolic Integration I: Transcendental
          Functions, Second Edition, Springer-Verlag, 2005, pp. 35-70

    """
    if type(f) is not tuple:
        p, q = f.as_numer_denom()
    else:
        p, q = f

    p, q = Poly(p, x, composite=False), Poly(q, x, composite=False)

    coeff, p, q = p.cancel(q)
    poly, p = p.div(q)

    result = poly.integrate(x).as_expr()

    if p.is_zero:
        return coeff*result

    g, h = ratint_ratpart(p, q, x)

    P, Q = h.as_numer_denom()

    P = Poly(P, x)
    Q = Poly(Q, x)

    q, r = P.div(Q)

    result += g + q.integrate(x).as_expr()

    if not r.is_zero:
        symbol = flags.get('symbol', 't')

        if not isinstance(symbol, Symbol):
            t = Dummy(symbol)
        else:
            t = symbol

        L = ratint_logpart(r, Q, x, t)

        real = flags.get('real')

        if real is None:
            if type(f) is not tuple:
                atoms = f.atoms()
            else:
                p, q = f

                atoms = p.atoms() \
                      | q.atoms()

            for elt in atoms - set([x]):
                if not elt.is_real:
                    real = False
                    break
            else:
                real = True

        eps = S(0)

        if not real:
            for h, q in L:
                eps += RootSum(q, Lambda(t, t*log(h.as_expr())), quadratic=True)
        else:
            for h, q in L:
                R = log_to_real(h, q, x, t)

                if R is not None:
                    eps += R
                else:
                    eps += RootSum(q, Lambda(t, t*log(h.as_expr())), quadratic=True)

        result += eps

    return coeff*result

def ratint_ratpart(f, g, x):
    """Horowitz-Ostrogradsky algorithm.

       Given a field K and polynomials f and g in K[x], such that f and g
       are coprime and deg(f) < deg(g), returns fractions A and B in K(x),
       such that f/g = A' + B and B has square-free denominator.

    """
    f = Poly(f, x)
    g = Poly(g, x)

    u, v, _ = g.cofactors(g.diff())

    n = u.degree()
    m = v.degree()
    d = g.degree()

    A_coeffs = [ Dummy('a' + str(n-i)) for i in range(0, n) ]
    B_coeffs = [ Dummy('b' + str(m-i)) for i in range(0, m) ]

    C_coeffs = A_coeffs + B_coeffs

    A = Poly(A_coeffs, x, domain=ZZ[C_coeffs])
    B = Poly(B_coeffs, x, domain=ZZ[C_coeffs])

    H = f - A.diff()*v + A*(u.diff()*v).quo(u) - B*u

    result = solve(H.coeffs(), C_coeffs)

    A = A.as_expr().subs(result)
    B = B.as_expr().subs(result)

    rat_part = cancel(A/u.as_expr(), x)
    log_part = cancel(B/v.as_expr(), x)

    return rat_part, log_part

def ratint_logpart(f, g, x, t=None):
    """Lazard-Rioboo-Trager algorithm.

       Given a field K and polynomials f and g in K[x], such that f and g
       are coprime, deg(f) < deg(g) and g is square-free, returns a list
       of tuples (s_i, q_i) of polynomials, for i = 1..n, such that s_i
       in K[t, x] and q_i in K[t], and:
                               ___    ___
                     d  f   d  \  `   \  `
                     -- - = --  )      )   a log(s_i(a, x))
                     dx g   dx /__,   /__,
                              i=1..n a | q_i(a) = 0

    """
    f, g = Poly(f, x), Poly(g, x)

    t = t or Dummy('t')
    a, b = g, f - g.diff()*Poly(t, x)

    R = subresultants(a, b)

    res = Poly(resultant(a, b), t, composite=False)

    R_map, H = {}, []

    for r in R:
        R_map[r.degree()] = r

    def _include_sign(c, sqf):
        if c < 0:
            h, k = sqf[0]
            sqf[0] = h*c, k

    C, res_sqf = res.sqf_list()
    _include_sign(C, res_sqf)

    for q, i in res_sqf:
        _, q = q.primitive()

        if g.degree() == i:
            H.append((g, q))
        else:
            h = R_map[i]
            h_lc = Poly(h.LC(), t, field=True)

            c, h_lc_sqf = h_lc.sqf_list(all=True)
            _include_sign(c, h_lc_sqf)

            for a, j in h_lc_sqf:
                h = h.quo(Poly(a.gcd(q)**j, x))

            inv, coeffs = h_lc.invert(q), [S(1)]

            for coeff in h.coeffs()[1:]:
                T = (inv*coeff).rem(q)
                coeffs.append(T.as_expr())

            h = Poly(dict(list(zip(h.monoms(), coeffs))), x)

            H.append((h, q))

    return H

def log_to_atan(f, g):
    """Convert complex logarithms to real arctangents.

       Given a real field K and polynomials f and g in K[x], with g != 0,
       returns a sum h of arctangents of polynomials in K[x], such that:

                       df   d         f + I g
                       -- = -- I log( ------- )
                       dx   dx        f - I g

    """
    if f.degree() < g.degree():
        f, g = -g, f

    f = f.to_field()
    g = g.to_field()

    p, q = f.div(g)

    if q.is_zero:
        return 2*atan(p.as_expr())
    else:
        s, t, h = g.gcdex(-f)
        u = (f*s+g*t).quo(h)
        A = 2*atan(u.as_expr())

        return A + log_to_atan(s, t)

def log_to_real(h, q, x, t):
    """Convert complex logarithms to real functions.

       Given real field K and polynomials h in K[t,x] and q in K[t],
       returns real function f such that:
                              ___
                      df   d  \  `
                      -- = --  )  a log(h(a, x))
                      dx   dx /__,
                             a | q(a) = 0

    """
    u, v = symbols('u,v')

    H = h.as_expr().subs({t:u+I*v}).expand()
    Q = q.as_expr().subs({t:u+I*v}).expand()

    H_map = collect(H, I, evaluate=False)
    Q_map = collect(Q, I, evaluate=False)

    a, b = H_map.get(S(1), S(0)), H_map.get(I, S(0))
    c, d = Q_map.get(S(1), S(0)), Q_map.get(I, S(0))

    R = Poly(resultant(c, d, v), u)

    R_u = roots(R, filter='R')

    if len(R_u) != R.count_roots():
        return None

    result = S(0)

    for r_u in R_u.keys():
        C = Poly(c.subs({u:r_u}), v)
        R_v = roots(C, filter='R')

        if len(R_v) != C.count_roots():
            return None

        for r_v in R_v:
            if not r_v.is_positive:
                continue

            D = d.subs({u:r_u, v:r_v})

            if D.evalf(chop=True) != 0:
                continue

            A = Poly(a.subs({u:r_u, v:r_v}), x)
            B = Poly(b.subs({u:r_u, v:r_v}), x)

            AB = (A**2 + B**2).as_expr()

            result += r_u*log(AB) + r_v*log_to_atan(A, B)

    R_q = roots(q, filter='R')

    if len(R_q) != q.count_roots():
        return None

    for r in R_q.keys():
        result += r*log(h.as_expr().subs(t, r))

    return result
