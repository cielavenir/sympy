"""Shor's algorithm and helper functions.

Todo:

* Get the CMod gate working again using the new Gate API.
* Fix everything.
* Update docstrings and reformat.
* Remove print statements. We may want to think about a better API for this.
"""
import math
import random

from sympy import Mul
from sympy import log, sqrt
from sympy.core.numbers import igcd

from sympy.physics.quantum.gate import Gate
from sympy.physics.quantum.qubit import Qubit, measure_partial_oneshot
from sympy.physics.quantum.qapply import qapply
from sympy.physics.quantum.qft import QFT
from sympy.physics.quantum.qexpr import QuantumError


class OrderFindingException(QuantumError):
    pass


class CMod(Gate):
    """A controlled mod gate.

    This is black box controlled Mod function for use by shor's algorithm.
    TODO implement a decompose property that returns how to do this in terms
    of elementary gates
    """

    @classmethod
    def _eval_args(cls, args):
        # t = args[0]
        # a = args[1]
        # N = args[2]
        raise NotImplementedError('The CMod gate has not been completed.')

    @property
    def t(self):
        """Size of 1/2 input register.  First 1/2 holds output."""
        return self.label[0]

    @property
    def a(self):
        """Base of the controlled mod function."""
        return self.label[1]

    @property
    def N(self):
        """N is the type of modular arithmetic we are doing."""
        return self.label[2]

    def _apply_operator_Qubit(self, qubits, **options):
        """
            This directly calculates the controlled mod of the second half of
            the register and puts it in the second
            This will look pretty when we get Tensor Symbolically working
        """
        n = 1
        k = 0
        # Determine the value stored in high memory.
        for i in range(self.t):
            k = k + n*qubits[self.t+i]
            n = n*2

        # The value to go in low memory will be out.
        out = int(self.a**k%self.N)

        # Create array for new qbit-ket which will have high memory unaffected
        outarray = list(qubits.args[0][0:self.t])

        # Place out in low memory
        for i in reversed(list(range(self.t))):
            outarray.append((out>>i)&1)

        return Qubit(*outarray)


def shor(N):
    """This function implements Shor's factoring algorithm on the Integer N

    The algorithm starts by picking a random number (a) and seeing if it is
    coprime with N. If it isn't, then the gcd of the two numbers is a factor
    and we are done. Otherwise, it begins the period_finding subroutine which
    finds the period of a in modulo N arithmetic. This period, if even, can
    be used to calculate factors by taking a**(r/2)-1 and a**(r/2)+1.
    These values are returned.
    """
    a = random.randrange(N-2)+2
    if igcd(N,a) != 1:
        print("got lucky with rand")
        return igcd(N,a)
    print("a= ",a)
    print("N= ",N)
    r = period_find(a,N)
    print("r= ",r)
    if r%2 == 1:
        print("r is not even, begin again")
        shor(N)
    answer = (igcd(a**(r/2)-1, N), igcd(a**(r/2)+1, N))
    return answer


def arr(num, t):
    """This function returns num as an array in binary

    It does this with the 0th digit being on the right

    >>> from sympy.physics.quantum.shor import arr
    >>> arr(5, 4)
    [0, 1, 0, 1]
    """
    binary_array = []
    for i in reversed(list(range(t))):
        binary_array.append((num>>i)&1)
    return binary_array


def getr(x, y, N):
    fraction = continued_fraction(x,y)
    # Now convert into r
    total = ratioize(fraction, N)
    return total


def ratioize(list, N):
    if list[0] > N:
        return 0
    if len(list) == 1:
        return list[0]
    return list[0] + ratioize(list[1:], N)


def continued_fraction(x, y):
    """This applies the continued fraction expansion to two numbers x/y

    x is the numerator and y is the denominator

    >>> from sympy.physics.quantum.shor import continued_fraction
    >>> continued_fraction(3, 8)
    [0, 2, 1, 2]
    """
    x = int(x)
    y = int(y)
    temp = x//y
    if temp*y == x:
        return [temp,]

    list = continued_fraction(y, x-temp*y)
    list.insert(0, temp)
    return list


def period_find(a, N):
    """Finds the period of a in modulo N arithmetic

    This is quantum part of Shor's algorithm.It takes two registers,
    puts first in superposition of states with Hadamards so: |k>|0>
    with k being all possible choices. It then does a controlled mod and
    a QFT to determine the order of a.
    """
    epsilon = .5
    #picks out t's such that maintains accuracy within epsilon
    t = int(2*math.ceil(log(N,2)))
    # make the first half of register be 0's |000...000>
    start = [0 for x in range(t)]
    #Put second half into superposition of states so we have |1>x|0> + |2>x|0> + ... |k>x>|0> + ... + |2**n-1>x|0>
    factor = 1/sqrt(2**t)
    qubits = 0
    for i in range(2**t):
        qbitArray = arr(i, t) + start
        qubits = qubits + Qubit(*qbitArray)
    circuit = (factor*qubits).expand()
    #Controlled second half of register so that we have:
    # |1>x|a**1 %N> + |2>x|a**2 %N> + ... + |k>x|a**k %N >+ ... + |2**n-1=k>x|a**k % n>
    circuit = CMod(t,a,N)*circuit
    #will measure first half of register giving one of the a**k%N's
    circuit = qapply(circuit)
    print("controlled Mod'd")
    for i in range(t):
        circuit = measure_partial_oneshot(circuit, i)
        # circuit = measure(i)*circuit
    # circuit = qapply(circuit)
    print("measured 1")
    #Now apply Inverse Quantum Fourier Transform on the second half of the register
    circuit = qapply(QFT(t, t*2).decompose()*circuit, floatingPoint = True)
    print("QFT'd")
    for i in range(t):
        circuit = measure_partial_oneshot(circuit, i+t)
        # circuit = measure(i+t)*circuit
    # circuit = qapply(circuit)
    print(circuit)
    if isinstance(circuit, Qubit):
        register = circuit
    elif isinstance(circuit, Mul):
        register = circuit.args[-1]
    else:
        register = circuit.args[-1].args[-1]

    print(register)
    n = 1
    answer = 0
    for i in range(len(register)/2):
        answer += n*register[i+t]
        n = n<<1
    if answer == 0:
        raise OrderFindingException("Order finder returned 0. Happens with chance %f" % epsilon)
    #turn answer into r using continued fractions
    g = getr(answer, 2**t, N)
    print(g)
    return g
