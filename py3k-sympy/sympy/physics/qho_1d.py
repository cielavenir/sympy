from sympy.core import S, pi, Rational
from sympy.functions import hermite, sqrt, exp, factorial
from sympy.physics.quantum.constants import hbar

def psi_n(n, x, m, omega):
    """
    Returns the wavefunction psi_{n} for the One-dimensional harmonic oscillator.

    ``n``
        the "nodal" quantum number.  Corresponds to the number of nodes in the
        wavefunction.  n >= 0
    ``x``
        x coordinate
    ``m``
        mass of the particle
    ``omega``
        angular frequency of the oscillator

    :Example:

    >>> from sympy.physics.qho_1d import psi_n
    >>> from sympy import var
    >>> var("x m omega")
    (x, m, omega)
    >>> psi_n(0, x, m, omega)
    (m*omega)**(1/4)*exp(-m*omega*x**2/(2*hbar))/(hbar**(1/4)*pi**(1/4))

    """

    # sympify arguments
    n, x, m, omega = list(map(S, [n, x, m, omega]))
    nu = m * omega / hbar
    # normalization coefficient
    C =  (nu/pi)**(S(1)/4) * sqrt(1/(2**n*factorial(n)))

    return  C * exp(-nu* x**2 /2) * hermite(n, sqrt(nu)*x)


def E_n(n,omega):
    """
    Returns the Energy of the One-dimensional harmonic oscillator

    ``n``
        the "nodal" quantum number
    ``omega``
        the harmonic oscillator angular frequency

    The unit of the returned value matches the unit of hw, since the energy is
    calculated as:

        E_n = hbar * omega*(n + 1/2)
    """

    return hbar * omega*(n + Rational(1,2))
