"""
Second quantization operators and states for bosons.

This follow the formulation of Fetter and Welecka, "Quantum Theory
of Many-Particle Systems."
"""

from sympy import (
    Basic, Expr, Function, Mul, sympify, Integer, Add, sqrt,
    zeros, Pow, I, S, Symbol, Tuple, Dummy
)

from sympy.core.sympify import sympify
from sympy.core.cache import cacheit
from sympy.core.symbol import Dummy
from sympy.printing.str import StrPrinter

from sympy.core.compatibility import reduce
from functools import reduce

__all__ = [
    'Dagger',
    'KroneckerDelta',
    'BosonicOperator',
    'AnnihilateBoson',
    'CreateBoson',
    'AnnihilateFermion',
    'CreateFermion',
    'FockState',
    'FockStateBra',
    'FockStateKet',
    'BBra',
    'BKet',
    'FBra',
    'FKet',
    'F',
    'Fd',
    'B',
    'Bd',
    'apply_operators',
    'InnerProduct',
    'BosonicBasis',
    'VarBosonicBasis',
    'FixedBosonicBasis',
    'Commutator',
    'matrix_rep',
    'contraction',
    'wicks',
    'NO',
    'evaluate_deltas',
    'AntiSymmetricTensor',
    'substitute_dummies',
    'PermutationOperator',
    'simplify_index_permutations',
]

class SecondQuantizationError(Exception):
    pass

class AppliesOnlyToSymbolicIndex(SecondQuantizationError):
    pass

class ContractionAppliesOnlyToFermions(SecondQuantizationError):
    pass

class ViolationOfPauliPrinciple(SecondQuantizationError):
    pass

class SubstitutionOfAmbigousOperatorFailed(SecondQuantizationError):
    pass

class WicksTheoremDoesNotApply(SecondQuantizationError):
    pass

class Dagger(Expr):
    """
    Hermitian conjugate of creation/annihilation operators.

    Example:

    >>> from sympy import I
    >>> from sympy.physics.secondquant import Dagger, B, Bd
    >>> Dagger(2*I)
    -2*I
    >>> Dagger(B(0))
    CreateBoson(0)
    >>> Dagger(Bd(0))
    AnnihilateBoson(0)

    """

    def __new__(cls, arg):
        arg = sympify(arg)
        r = cls.eval(arg)
        if isinstance(r, Basic):
            return r
        obj = Basic.__new__(cls, arg)
        return obj

    @classmethod
    def eval(cls, arg):
        """
        Evaluates the Dagger instance.

        Example:

        >>> from sympy import I
        >>> from sympy.physics.secondquant import Dagger, B, Bd
        >>> Dagger(2*I)
        -2*I
        >>> Dagger(B(0))
        CreateBoson(0)
        >>> Dagger(Bd(0))
        AnnihilateBoson(0)

        The eval() method is called automatically.

        """
        try:
            d = arg._dagger_()
        except:
            if isinstance(arg, Basic):
                if arg.is_Add:
                    return Add(*tuple(map(Dagger, arg.args)))
                if arg.is_Mul:
                    return Mul(*tuple(map(Dagger, reversed(arg.args))))
                if arg.is_Number:
                    return arg
                if arg.is_Pow:
                    return Pow(Dagger(arg.args[0]),arg.args[1])
                if arg == I:
                    return -arg
            else:
                return None
        else:
            return d

    def _eval_subs(self, old, new):
        if self == old:
            return new
        r = Dagger(self.args[0].subs(old, new))
        return r

    def _dagger_(self):
        return self.args[0]


class TensorSymbol(Expr):

    is_commutative = True


class AntiSymmetricTensor(TensorSymbol):
    """Stores upper and lower indices in separate Tuple's.

    Each group of indices is assumed to be antisymmetric.

    Examples:

    >>> from sympy import symbols
    >>> from sympy.physics.secondquant import AntiSymmetricTensor
    >>> i, j = symbols('i j', below_fermi=True)
    >>> a, b = symbols('a b', above_fermi=True)
    >>> AntiSymmetricTensor('v', (a, i), (b, j))
    AntiSymmetricTensor(v, (a, i), (b, j))
    >>> AntiSymmetricTensor('v', (i, a), (b, j))
    -AntiSymmetricTensor(v, (a, i), (b, j))

    As you can see, the indices are automatically sorted to a canonical form.

    """

    nargs = 3

    def __new__(cls, symbol, upper, lower):

        try:
            upper, signu = _sort_anticommuting_fermions(upper, key=cls._sortkey)
            lower, signl = _sort_anticommuting_fermions(lower, key=cls._sortkey)

        except ViolationOfPauliPrinciple:
            return S.Zero

        symbol = sympify(symbol)
        upper = Tuple(*upper)
        lower = Tuple(*lower)

        if (signu + signl) % 2:
            return -TensorSymbol.__new__(cls, symbol, upper, lower)
        else:
            return  TensorSymbol.__new__(cls, symbol, upper, lower)

    @classmethod
    def _sortkey(cls, index):
        """Key for sorting of indices.

        particle < hole < general

        FIXME: This is a bottle-neck, can we do it faster?
        """
        h = hash(index)
        if isinstance(index, Dummy):
            if index.assumptions0.get('above_fermi'):
                return (20, h)
            elif index.assumptions0.get('below_fermi'):
                return (21, h)
            else:
                return (22, h)

        if index.assumptions0.get('above_fermi'):
            return (10, h)
        elif index.assumptions0.get('below_fermi'):
            return (11, h)
        else:
            return (12, h)


    def _latex(self,printer):
        return "%s^{%s}_{%s}" %(
                self.symbol,
                "".join([ i.name for i in self.args[1]]),
                "".join([ i.name for i in self.args[2]])
                )

    @property
    def symbol(self):
        """
        Returns the symbol of the tensor.

        Example:

        >>> from sympy import symbols
        >>> from sympy.physics.secondquant import AntiSymmetricTensor
        >>> i, j = symbols('i,j', below_fermi=True)
        >>> a, b = symbols('a,b', above_fermi=True)
        >>> AntiSymmetricTensor('v', (a, i), (b, j))
        AntiSymmetricTensor(v, (a, i), (b, j))
        >>> AntiSymmetricTensor('v', (a, i), (b, j)).symbol
        v

        """
        return self.args[0]

    @property
    def upper(self):
        """
        Returns the upper indices.

        Example:

        >>> from sympy import symbols
        >>> from sympy.physics.secondquant import AntiSymmetricTensor
        >>> i, j = symbols('i,j', below_fermi=True)
        >>> a, b = symbols('a,b', above_fermi=True)
        >>> AntiSymmetricTensor('v', (a, i), (b, j))
        AntiSymmetricTensor(v, (a, i), (b, j))
        >>> AntiSymmetricTensor('v', (a, i), (b, j)).upper
        (a, i)


        """
        return self.args[1]

    @property
    def lower(self):
        """
        Returns the lower indices.

        Example:

        >>> from sympy import symbols
        >>> from sympy.physics.secondquant import AntiSymmetricTensor
        >>> i, j = symbols('i,j', below_fermi=True)
        >>> a, b = symbols('a,b', above_fermi=True)
        >>> AntiSymmetricTensor('v', (a, i), (b, j))
        AntiSymmetricTensor(v, (a, i), (b, j))
        >>> AntiSymmetricTensor('v', (a, i), (b, j)).lower
        (b, j)

        """
        return self.args[2]

    def __str__(self):
        return "%s(%s,%s)" %self.args

    def doit(self, **kw_args):
        return self


class KroneckerDelta(Function):
    """
    Discrete delta function.

    >>> from sympy import symbols
    >>> from sympy.physics.secondquant import KroneckerDelta
    >>> i, j, k = symbols('i,j,k')
    >>> KroneckerDelta(i, j)
    KroneckerDelta(i, j)
    >>> KroneckerDelta(i, i)
    1
    >>> KroneckerDelta(i, i+1)
    0
    >>> KroneckerDelta(i, i+1+k)
    KroneckerDelta(i, i + k + 1)

    """

    nargs = 2
    is_commutative=True

    @classmethod
    def eval(cls, i, j):
        """
        Evaluates the discrete delta function.

        >>> from sympy import symbols
        >>> from sympy.physics.secondquant import KroneckerDelta
        >>> i, j, k = symbols('i,j,k')
        >>> KroneckerDelta(i, j)
        KroneckerDelta(i, j)
        >>> KroneckerDelta(i, i)
        1
        >>> KroneckerDelta(i, i+1)
        0
        >>> KroneckerDelta(i, i+1+k)
        KroneckerDelta(i, i + k + 1)

        # indirect doctest

        """
        if i > j:
            return cls(j,i)
        diff = i-j
        if diff == 0:
            return S.One
        elif diff.is_number:
            return S.Zero

        if i.assumptions0.get("below_fermi") and j.assumptions0.get("above_fermi"):
            return S.Zero
        if j.assumptions0.get("below_fermi") and i.assumptions0.get("above_fermi"):
            return S.Zero

    def _eval_subs(self, old, new):
        if self == old:
            return new
        r = KroneckerDelta(self.args[0].subs(old, new), self.args[1].subs(old, new))
        return r

    @property
    def is_above_fermi(self):
        """
        True if Delta can be non-zero above fermi

        >>> from sympy.physics.secondquant import KroneckerDelta
        >>> from sympy import Symbol
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')
        >>> q = Symbol('q')
        >>> KroneckerDelta(p,a).is_above_fermi
        True
        >>> KroneckerDelta(p,i).is_above_fermi
        False
        >>> KroneckerDelta(p,q).is_above_fermi
        True

        """
        if self.args[0].assumptions0.get("below_fermi"):
            return False
        if self.args[1].assumptions0.get("below_fermi"):
            return False
        return True

    @property
    def is_below_fermi(self):
        """
        True if Delta can be non-zero below fermi

        >>> from sympy.physics.secondquant import KroneckerDelta
        >>> from sympy import Symbol
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')
        >>> q = Symbol('q')
        >>> KroneckerDelta(p,a).is_below_fermi
        False
        >>> KroneckerDelta(p,i).is_below_fermi
        True
        >>> KroneckerDelta(p,q).is_below_fermi
        True

        """
        if self.args[0].assumptions0.get("above_fermi"):
            return False
        if self.args[1].assumptions0.get("above_fermi"):
            return False
        return True

    @property
    def is_only_above_fermi(self):
        """
        True if Delta is restricted to above fermi

        >>> from sympy.physics.secondquant import KroneckerDelta
        >>> from sympy import Symbol
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')
        >>> q = Symbol('q')
        >>> KroneckerDelta(p,a).is_only_above_fermi
        True
        >>> KroneckerDelta(p,q).is_only_above_fermi
        False
        >>> KroneckerDelta(p,i).is_only_above_fermi
        False

        """
        return ( self.args[0].assumptions0.get("above_fermi")
                or
                self.args[1].assumptions0.get("above_fermi")
                ) or False

    @property
    def is_only_below_fermi(self):
        """
        True if Delta is restricted to below fermi

        >>> from sympy.physics.secondquant import KroneckerDelta
        >>> from sympy import Symbol
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')
        >>> q = Symbol('q')
        >>> KroneckerDelta(p,i).is_only_below_fermi
        True
        >>> KroneckerDelta(p,q).is_only_below_fermi
        False
        >>> KroneckerDelta(p,a).is_only_below_fermi
        False

        """
        return ( self.args[0].assumptions0.get("below_fermi")
                or
                self.args[1].assumptions0.get("below_fermi")
                ) or False

    @property
    def indices_contain_equal_information(self):
        """
        Returns True if indices are either both above or below fermi.

        Example:

        >>> from sympy.physics.secondquant import KroneckerDelta
        >>> from sympy import Symbol
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')
        >>> q = Symbol('q')
        >>> KroneckerDelta(p, q).indices_contain_equal_information
        True
        >>> KroneckerDelta(p, q+1).indices_contain_equal_information
        True
        >>> KroneckerDelta(i, p).indices_contain_equal_information
        False

        """
        if (self.args[0].assumptions0.get("below_fermi") and
                self.args[1].assumptions0.get("below_fermi")):
            return True
        if (self.args[0].assumptions0.get("above_fermi")
                and self.args[1].assumptions0.get("above_fermi")):
            return True

        # if both indices are general we are True, else false
        return self.is_below_fermi and self.is_above_fermi


    @property
    def preferred_index(self):
        """
        Returns the index which is preferred to keep in the final expression.

        The preferred index is the index with more information regarding fermi
        level.  If indices contain same information, 'a' is preferred before
        'b'.

        >>> from sympy.physics.secondquant import KroneckerDelta
        >>> from sympy import Symbol
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> j = Symbol('j',below_fermi=True)
        >>> p = Symbol('p')
        >>> KroneckerDelta(p,i).preferred_index
        i
        >>> KroneckerDelta(p,a).preferred_index
        a
        >>> KroneckerDelta(i,j).preferred_index
        i

        """
        if self._get_preferred_index():
            return self.args[1]
        else:
            return self.args[0]

    @property
    def killable_index(self):
        """
        Returns the index which is preferred to substitute in the final expression.

        The index to substitute is the index with less information regarding fermi
        level.  If indices contain same information, 'a' is preferred before
        'b'.

        >>> from sympy.physics.secondquant import KroneckerDelta
        >>> from sympy import Symbol
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> j = Symbol('j',below_fermi=True)
        >>> p = Symbol('p')
        >>> KroneckerDelta(p,i).killable_index
        p
        >>> KroneckerDelta(p,a).killable_index
        p
        >>> KroneckerDelta(i,j).killable_index
        j

        """
        if self._get_preferred_index():
            return self.args[0]
        else:
            return self.args[1]

    def _get_preferred_index(self):
        """
        Returns the index which is preferred to keep in the final expression.

        The preferred index is the index with more information regarding fermi
        level.  If indices contain same information, index 0 is returned.
        """
        if not self.is_above_fermi:
            if self.args[0].assumptions0.get("below_fermi"):
                return 0
            else:
                return 1
        elif not self.is_below_fermi:
            if self.args[0].assumptions0.get("above_fermi"):
                return 0
            else:
                return 1
        else:
            return 0

    def _dagger_(self):
        return self

    def _latex(self,printer):
        return "\\delta_{%s%s}"% (self.args[0].name,self.args[1].name)

    def __repr__(self):
        return "KroneckerDelta(%s,%s)"% (self.args[0],self.args[1])

    def __str__(self):
        if not self.is_above_fermi:
            return 'd<(%s,%s)'% (self.args[0],self.args[1])
        elif not self.is_below_fermi:
            return 'd>(%s,%s)'% (self.args[0],self.args[1])
        else:
            return 'd(%s,%s)'% (self.args[0],self.args[1])



class SqOperator(Expr):
    """
    Base class for Second Quantization operators.
    """

    op_symbol = 'sq'

    def __new__(cls, k):
        obj = Basic.__new__(cls, sympify(k), commutative=False)
        return obj

    def _eval_subs(self, old, new):
        if self == old:
            return new
        r = self.__class__(self.args[0].subs(old, new))
        return r

    @property
    def state(self):
        """
        Returns the state index related to this operator.

        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import F, Fd, B, Bd
        >>> p = Symbol('p')
        >>> F(p).state
        p
        >>> Fd(p).state
        p
        >>> B(p).state
        p
        >>> Bd(p).state
        p

        """
        return self.args[0]

    @property
    def is_symbolic(self):
        """
        Returns True if the state is a symbol (as opposed to a number).

        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import F
        >>> p = Symbol('p')
        >>> F(p).is_symbolic
        True
        >>> F(1).is_symbolic
        False

        """
        if self.state.is_Integer:
            return False
        else:
            return True

    def doit(self,**kw_args):
        """
        FIXME: hack to prevent crash further up...
        """
        return self

    def __repr__(self):
        return NotImplemented

    def __str__(self):
        return "%s(%r)" % (self.op_symbol, self.state)

    def apply_operator(self, state):
        """
        Applies an operator to itself.
        """
        raise NotImplementedError('implement apply_operator in a subclass')

class BosonicOperator(SqOperator):
    pass

class Annihilator(SqOperator):
    pass

class Creator(SqOperator):
    pass


class AnnihilateBoson(BosonicOperator, Annihilator):
    """
    Bosonic annihilation operator
    """

    op_symbol = 'b'

    def _dagger_(self):
        return CreateBoson(self.state)

    def apply_operator(self, state):
        if not self.is_symbolic and isinstance(state, FockStateKet):
            element = self.state
            amp = sqrt(state[element])
            return amp*state.down(element)
        else:
            return Mul(self,state)

    def __repr__(self):
        return "AnnihilateBoson(%s)"%self.state

class CreateBoson(BosonicOperator, Creator):
    """
    Bosonic creation operator
    """

    op_symbol = 'b+'

    def _dagger_(self):
        return AnnihilateBoson(self.state)

    def apply_operator(self, state):
        if not self.is_symbolic and isinstance(state, FockStateKet):
            element = self.state
            amp = sqrt(state[element] + 1)
            return amp*state.up(element)
        else:
            return Mul(self,state)

    def __repr__(self):
        return "CreateBoson(%s)"%self.state

B = AnnihilateBoson
Bd = CreateBoson


class FermionicOperator(SqOperator):

    @property
    def is_restricted(self):
        """
        Is this FermionicOperator restricted with respect to fermi level?

        Return values:
        1  : restricted to orbits above fermi
        0  : no restriction
        -1 : restricted to orbits below fermi

        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import F, Fd
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')

        >>> F(a).is_restricted
        1
        >>> Fd(a).is_restricted
        1
        >>> F(i).is_restricted
        -1
        >>> Fd(i).is_restricted
        -1
        >>> F(p).is_restricted
        0
        >>> Fd(p).is_restricted
        0

        """
        ass = self.args[0].assumptions0
        if ass.get("below_fermi"): return -1
        if ass.get("above_fermi"): return  1
        return 0


    @property
    def is_above_fermi(self):
        """
        Does the index of this FermionicOperator allow values above fermi?


        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import F
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')

        >>> F(a).is_above_fermi
        True
        >>> F(i).is_above_fermi
        False
        >>> F(p).is_above_fermi
        True

        The same applies to creation operators Fd

        """
        return not self.args[0].assumptions0.get("below_fermi")

    @property
    def is_below_fermi(self):
        """
        Does the index of this FermionicOperator allow values below fermi?

        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import F
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')

        >>> F(a).is_below_fermi
        False
        >>> F(i).is_below_fermi
        True
        >>> F(p).is_below_fermi
        True

        The same applies to creation operators Fd

        """
        return not self.args[0].assumptions0.get("above_fermi")

    @property
    def is_only_below_fermi(self):
        """
        Is the index of this FermionicOperator restricted to values below fermi?

        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import F
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')

        >>> F(a).is_only_below_fermi
        False
        >>> F(i).is_only_below_fermi
        True
        >>> F(p).is_only_below_fermi
        False

        The same applies to creation operators Fd
        """
        return self.is_below_fermi and not self.is_above_fermi

    @property
    def is_only_above_fermi(self):
        """
        Is the index of this FermionicOperator restricted to values above fermi?

        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import F
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')

        >>> F(a).is_only_above_fermi
        True
        >>> F(i).is_only_above_fermi
        False
        >>> F(p).is_only_above_fermi
        False

        The same applies to creation operators Fd
        """
        return self.is_above_fermi and not self.is_below_fermi

    def _sortkey(self):
        h = hash(self)

        if self.is_only_q_creator:
            return 1, h
        if self.is_only_q_annihilator:
            return 4, h
        if isinstance(self, Annihilator):
            return 3, h
        if isinstance(self, Creator):
            return 2, h


class AnnihilateFermion(FermionicOperator, Annihilator):
    """
    Fermionic annihilation operator
    """

    op_symbol = 'f'

    def _dagger_(self):
        return CreateFermion(self.state)

    def apply_operator(self, state):
        if isinstance(state, FockStateFermionKet):
            element = self.state
            return state.down(element)

        elif isinstance(state, Mul):
            c_part, nc_part = split_commutative_parts(state)
            if isinstance(nc_part[0], FockStateFermionKet):
                element = self.state
                return Mul(*(c_part+[nc_part[0].down(element)]+nc_part[1:]))
            else:
                return Mul(self,state)

        else:
            return Mul(self,state)

    @property
    def is_q_creator(self):
        """
        Can we create a quasi-particle?  (create hole or create particle)
        If so, would that be above or below the fermi surface?

        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import F
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')

        >>> F(a).is_q_creator
        0
        >>> F(i).is_q_creator
        -1
        >>> F(p).is_q_creator
        -1

        """
        if self.is_below_fermi: return -1
        return 0

    @property
    def is_q_annihilator(self):
        """
        Can we destroy a quasi-particle?  (annihilate hole or annihilate particle)
        If so, would that be above or below the fermi surface?

        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import F
        >>> a = Symbol('a',above_fermi=1)
        >>> i = Symbol('i',below_fermi=1)
        >>> p = Symbol('p')

        >>> F(a).is_q_annihilator
        1
        >>> F(i).is_q_annihilator
        0
        >>> F(p).is_q_annihilator
        1

        """
        if self.is_above_fermi: return 1
        return 0

    @property
    def is_only_q_creator(self):
        """
        Always create a quasi-particle?  (create hole or create particle)


        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import F
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')

        >>> F(a).is_only_q_creator
        False
        >>> F(i).is_only_q_creator
        True
        >>> F(p).is_only_q_creator
        False

        """
        return self.is_only_below_fermi

    @property
    def is_only_q_annihilator(self):
        """
        Always destroy a quasi-particle?  (annihilate hole or annihilate particle)

        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import F
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')

        >>> F(a).is_only_q_annihilator
        True
        >>> F(i).is_only_q_annihilator
        False
        >>> F(p).is_only_q_annihilator
        False

        """
        return self.is_only_above_fermi

    def __repr__(self):
        return "AnnihilateFermion(%s)"%self.state

    def _latex(self,printer):
        return "a_{%s}"%self.state.name

class CreateFermion(FermionicOperator, Creator):
    """
    Fermionic creation operator.
    """

    op_symbol = 'f+'

    def _dagger_(self):
        return AnnihilateFermion(self.state)

    def apply_operator(self, state):
        if isinstance(state, FockStateFermionKet):
            element = self.state
            return state.up(element)


        elif isinstance(state, Mul):
            c_part, nc_part = split_commutative_parts(state)
            if isinstance(nc_part[0], FockStateFermionKet):
                element = self.state
                return Mul(*(c_part+[nc_part[0].up(element)]+nc_part[1:]))
            else:
                return Mul(self,state)
        else:
            return Mul(self,state)

    @property
    def is_q_creator(self):
        """
        Can we create a quasi-particle?  (create hole or create particle)
        If so, would that be above or below the fermi surface?

        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import Fd
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')

        >>> Fd(a).is_q_creator
        1
        >>> Fd(i).is_q_creator
        0
        >>> Fd(p).is_q_creator
        1

        """
        if self.is_above_fermi: return 1
        return 0

    @property
    def is_q_annihilator(self):
        """
        Can we destroy a quasi-particle?  (annihilate hole or annihilate particle)
        If so, would that be above or below the fermi surface?

        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import Fd
        >>> a = Symbol('a',above_fermi=1)
        >>> i = Symbol('i',below_fermi=1)
        >>> p = Symbol('p')

        >>> Fd(a).is_q_annihilator
        0
        >>> Fd(i).is_q_annihilator
        -1
        >>> Fd(p).is_q_annihilator
        -1

        """
        if self.is_below_fermi: return -1
        return 0

    @property
    def is_only_q_creator(self):
        """
        Always create a quasi-particle?  (create hole or create particle)

        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import Fd
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')

        >>> Fd(a).is_only_q_creator
        True
        >>> Fd(i).is_only_q_creator
        False
        >>> Fd(p).is_only_q_creator
        False

        """
        return self.is_only_above_fermi

    @property
    def is_only_q_annihilator(self):
        """
        Always destroy a quasi-particle?  (annihilate hole or annihilate particle)

        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import Fd
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')

        >>> Fd(a).is_only_q_annihilator
        False
        >>> Fd(i).is_only_q_annihilator
        True
        >>> Fd(p).is_only_q_annihilator
        False

        """
        return self.is_only_below_fermi

    def __repr__(self):
        return "CreateFermion(%s)"%self.state

    def _latex(self,printer):
        return "a^\\dagger_{%s}"%self.state.name

Fd = CreateFermion
F = AnnihilateFermion



class FockState(Expr):
    """
    Many particle Fock state with a sequence of occupation numbers.

    Anywhere you can have a FockState, you can also have S.Zero.
    All code must check for this!
    """

    def __new__(cls, occupations):
        """
        occupations is a list with two possible meanings:

        - For bosons it is a list of occupation numbers.
          Element i is the number of particles in state i.

        - For fermions it is a list of occupied orbits.
          Element 0 is the state that was occupied first, element i
          is the i'th occupied state.
        """
        occupations = list(map(sympify, occupations))
        obj = Basic.__new__(cls, Tuple(*occupations), commutative=False)
        return obj

    def _eval_subs(self, old, new):
        if self == old:
            return new
        r = self.__class__([o.subs(old, new) for o in self.args[0]])
        return r


    def __getitem__(self, i):
        i = int(i)
        return self.args[0][i]

    def __repr__(self):
        return ("FockState(%r)") % (self.args)

    def __str__(self):
        return "%s%r%s" % (self.lbracket,self._labels(),self.rbracket)

    def _labels(self):
        return self.args[0]

    def __len__(self):
        return len(self.args[0])

class BosonState(FockState):
    """
    Many particle Fock state with a sequence of occupation numbers.

    occupation numbers can be any integer >= 0
    """

    def up(self, i):
        i = int(i)
        new_occs = list(self.args[0])
        new_occs[i] = new_occs[i]+S.One
        return self.__class__(new_occs)

    def down(self, i):
        i = int(i)
        new_occs = list(self.args[0])
        if new_occs[i]==S.Zero:
            return S.Zero
        else:
            new_occs[i] = new_occs[i]-S.One
            return self.__class__(new_occs)


class FermionState(FockState):
    """
    Many particle Fock state with a sequence of occupied orbits

    Each state can only have one particle, so we choose to store a list of
    occupied orbits rather than a tuple with occupation numbers (zeros and ones).

    states below fermi level are holes, and are represented by negative labels
    in the occupation list

    For symbolic state labels, the fermi_level caps the number of allowed hole-
    states

    """

    fermi_level=0

    def __new__(cls, occupations, fermi_level=0):
        occupations = list(map(sympify,occupations))
        if len(occupations) >1:
            try:
                (occupations,sign) = _sort_anticommuting_fermions(occupations, key=hash)
            except ViolationOfPauliPrinciple:
                return S.Zero
        else:
            sign = 0

        cls.fermi_level = fermi_level

        if cls._count_holes(occupations) > fermi_level:
            return S.Zero


        if sign%2:
            return S.NegativeOne*FockState.__new__(cls,occupations)
        else:
            return FockState.__new__(cls,occupations)

    def up(self, i):
        """
        Performs the action of a creation operator.

        If below fermi we try to remove a hole,
        if above fermi we try to create a particle.

        if general index p we return Kronecker(p,i)*self
        where i is a new symbol with restriction above or below.

        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import FKet
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')

        >>> FKet([]).up(a)
        FockStateFermionKet((a,))

        A creator acting on vacuum below fermi vanishes
        >>> FKet([]).up(i)
        0


        """
        present = i in self.args[0]

        if self._only_above_fermi(i):
            if present:
                return S.Zero
            else:
                return self._add_orbit(i)
        elif self._only_below_fermi(i):
            if present:
                return self._remove_orbit(i)
            else:
                return S.Zero
        else:
            if present:
                hole = Dummy("i",below_fermi=True)
                return KroneckerDelta(i,hole)*self._remove_orbit(i)
            else:
                particle = Dummy("a",above_fermi=True)
                return KroneckerDelta(i,particle)*self._add_orbit(i)

    def down(self, i):
        """
        Performs the action of an annihilation operator.

        If below fermi we try to create a hole,
        if above fermi we try to remove a particle.

        if general index p we return Kronecker(p,i)*self
        where i is a new symbol with restriction above or below.

        >>> from sympy import Symbol
        >>> from sympy.physics.secondquant import FKet
        >>> a = Symbol('a',above_fermi=True)
        >>> i = Symbol('i',below_fermi=True)
        >>> p = Symbol('p')

        An annihilator acting on vacuum above fermi vanishes
        >>> FKet([]).down(a)
        0

        Also below fermi, it vanishes, unless we specify a fermi level > 0
        >>> FKet([]).down(i)
        0
        >>> FKet([],4).down(i)
        FockStateFermionKet((i,))

        """
        present = i in self.args[0]

        if self._only_above_fermi(i):
            if present:
                return self._remove_orbit(i)
            else:
                return S.Zero

        elif self._only_below_fermi(i):
            if present:
                return S.Zero
            else:
                return self._add_orbit(i)
        else:
            if present:
                hole = Dummy("i",below_fermi=True)
                return KroneckerDelta(i,hole)*self._add_orbit(i)
            else:
                particle = Dummy("a",above_fermi=True)
                return KroneckerDelta(i,particle)*self._remove_orbit(i)



    @classmethod
    def _only_below_fermi(cls,i):
        """
        Tests if given orbit is only below fermi surface.

        If nothing can be concluded we return a conservative False.
        """
        if i.is_number:
            return i<= cls.fermi_level
        if i.assumptions0.get('below_fermi'):
            return True
        return False


    @classmethod
    def _only_above_fermi(cls,i):
        """
        Tests if given orbit is only above fermi surface.

        If fermi level has not been set we return True.
        If nothing can be concluded we return a conservative False.
        """
        if i.is_number:
            return i> cls.fermi_level
        if i.assumptions0.get('above_fermi'):
            return True
        return not cls.fermi_level


    def _remove_orbit(self,i):
        """
        Removes particle/fills hole in orbit i. No input tests performed here.
        """
        new_occs = list(self.args[0])
        pos = new_occs.index(i)
        del new_occs[pos]
        if (pos)%2:
            return S.NegativeOne*self.__class__(new_occs,self.fermi_level)
        else:
            return self.__class__(new_occs, self.fermi_level)

    def _add_orbit(self,i):
        """
        Adds particle/creates hole in orbit i. No input tests performed here.
        """
        return self.__class__((i,)+self.args[0], self.fermi_level)

    @classmethod
    def _count_holes(cls,list):
        """
        returns number of identified hole states in list.
        """
        return len([ i for i in list if  cls._only_below_fermi(i)])

    def _negate_holes(self,list):
        return tuple([ -i if i<=self.fermi_level else i for i in list ])

    def __repr__(self):
        if self.fermi_level:
            return "FockStateKet(%r, fermi_level=%s)"%(self.args[0],self.fermi_level)
        else:
            return "FockStateKet(%r)"%(self.args[0],)

    def _labels(self):
        return self._negate_holes(self.args[0])



class FockStateKet(FockState):

    lbracket = '|'
    rbracket = '>'


class FockStateBra(FockState):


    lbracket = '<'
    rbracket = '|'


    def __mul__(self, other):
        if isinstance(other, FockStateKet):
            return InnerProduct(self, other)
        else:
            return Expr.__mul__(self, other)

class FockStateBosonKet(BosonState,FockStateKet):
    def _dagger_(self):
        return FockStateBosonBra(*self.args)

class FockStateBosonBra(BosonState,FockStateBra):
    def _dagger_(self):
        return FockStateBosonKet(*self.args)

class FockStateFermionKet(FermionState,FockStateKet):
    def _dagger_(self):
        return FockStateFermionBra(*self.args)

class FockStateFermionBra(FermionState,FockStateBra):
    def _dagger_(self):
        return FockStateFermionKet(*self.args)

BBra = FockStateBosonBra
BKet = FockStateBosonKet
FBra = FockStateFermionBra
FKet = FockStateFermionKet

def split_commutative_parts(m):
    c_part = [p for p in m.args if p.is_commutative]
    nc_part = [p for p in m.args if not p.is_commutative]
    return c_part, nc_part


def apply_Mul(m):
    """
    Take a Mul instance with operators and apply them to states.

    This method applies all operators with integer state labels
    to the actual states.  For symbolic state labels, nothing is done.
    When inner products of FockStates are encountered (like <a|b>),
    the are converted to instances of InnerProduct.

    This does not currently work on double inner products like,
    <a|b><c|d>.

    If the argument is not a Mul, it is simply returned as is.
    """
    if not isinstance(m, Mul):
        return m
    c_part, nc_part = split_commutative_parts(m)
    n_nc = len(nc_part)
    if n_nc == 0 or n_nc == 1:
        return m
    else:
        last = nc_part[-1]
        next_to_last = nc_part[-2]
        if isinstance(last, FockStateKet):
            if isinstance(next_to_last, SqOperator):
                if next_to_last.is_symbolic:
                    return m
                else:
                    result = next_to_last.apply_operator(last)
                    if result == 0:
                        return 0
                    else:
                        return apply_Mul(Mul(*(c_part+nc_part[:-2]+[result])))
            elif isinstance(next_to_last, Pow):
                if isinstance(next_to_last.base, SqOperator) and \
                    next_to_last.exp.is_Integer:
                    if next_to_last.base.is_symbolic:
                        return m
                    else:
                        result = last
                        for i in range(next_to_last.exp):
                            result = next_to_last.base.apply_operator(result)
                            if result == 0: break
                        if result == 0:
                            return 0
                        else:
                            return apply_Mul(Mul(*(c_part+nc_part[:-2]+[result])))
                else:
                    return m
            elif isinstance(next_to_last, FockStateBra):
                result = InnerProduct(next_to_last, last)
                if result == 0:
                    return 0
                else:
                    return apply_Mul(Mul(*(c_part+nc_part[:-2]+[result])))
            else:
                return m
        else:
            return m


def apply_operators(e):
    """
    Take a sympy expression with operators and states and apply the operators.
    """
    e = e.expand()
    muls = e.atoms(Mul)
    subs_list = [(m,apply_Mul(m)) for m in iter(muls)]
    return e.subs(subs_list)


class InnerProduct(Basic):
    """
    An unevaluated inner product between a bra and ket.

    Currently this class just reduces things to a product of
    Kronecker Deltas.  In the future, we could introduce abstract
    states like |a> and |b>, and leave the inner product unevaluated as
    <a|b>.

    """
    def __new__(cls, bra, ket):
        assert isinstance(bra, FockStateBra), 'must be a bra'
        assert isinstance(ket, FockStateKet), 'must be a key'
        r = cls.eval(bra, ket)
        if isinstance(r, Basic):
            return r
        obj = Basic.__new__(cls, *(bra, ket), **dict(commutative=True))
        return obj

    @classmethod
    def eval(cls, bra, ket):
        result = S.One
        for i,j in zip(bra.args[0], ket.args[0]):
            result *= KroneckerDelta(i,j)
            if result == 0: break
        return result

    @property
    def bra(self):
        return self.args[0]

    @property
    def ket(self):
        return self.args[1]

    def _eval_subs(self, old, new):
        if self == old:
            return new
        r = self.__class__(self.bra.subs(old,new), self.ket.subs(old,new))
        return r

    def __repr__(self):
        sbra = repr(self.bra)
        sket = repr(self.ket)
        return "%s|%s" % (sbra[:-1], sket[1:])

    def __str__(self):
        return self.__repr__()


def matrix_rep(op, basis):
    """
    Find the representation of an operator in a basis.
    """
    a = zeros((len(basis), len(basis)))
    for i in range(len(basis)):
        for j in range(len(basis)):
            a[i,j] = apply_operators(Dagger(basis[i])*op*basis[j])
    return a


class BosonicBasis(object):
    """
    Base class for a basis set of bosonic Fock states.
    """
    pass


class VarBosonicBasis(object):
    """
    A single state, variable particle number basis set.
    """

    def __init__(self, n_max):
        self.n_max = n_max
        self._build_states()

    def _build_states(self):
        self.basis = []
        for i in range(self.n_max):
            self.basis.append(FockStateBosonKet([i]))
        self.n_basis = len(self.basis)

    def index(self, state):
        return self.basis.index(state)

    def state(self, i):
        return self.basis[i]

    def __getitem__(self, i):
        return self.state(i)

    def __len__(self):
        return len(self.basis)

    def __repr__(self):
        return repr(self.basis)


class FixedBosonicBasis(BosonicBasis):
    """
    Fixed particle number basis set.
    """
    def __init__(self, n_particles, n_levels):
        self.n_particles = n_particles
        self.n_levels = n_levels
        self._build_particle_locations()
        self._build_states()

    def _build_particle_locations(self):
        tup = ["i%i" % i for i in range(self.n_particles)]
        first_loop = "for i0 in range(%i)" % self.n_levels
        other_loops = ''
        for cur, prev in zip(tup[1:], tup):
            temp = "for %s in range(%s + 1) " % (cur, prev)
            other_loops = other_loops + temp
        tup_string = "(%s)" % ", ".join(tup)
        list_comp = "[%s %s %s]" % (tup_string, first_loop, other_loops)
        result = eval(list_comp)
        if self.n_particles == 1:
            result = [(item,) for item in result]
        self.particle_locations = result

    def _build_states(self):
        self.basis = []
        for tuple_of_indices in self.particle_locations:
            occ_numbers = self.n_levels*[0]
            for level in tuple_of_indices:
                occ_numbers[level] += 1
            self.basis.append(FockStateBosonKet(occ_numbers))
        self.n_basis = len(self.basis)

    def index(self, state):
        return self.basis.index(state)

    def state(self, i):
        return self.basis[i]

    def __getitem__(self, i):
        return self.state(i)

    def __len__(self):
        return len(self.basis)

    def __repr__(self):
        return repr(self.basis)


# def move(e, i, d):
#     """
#     Takes the expression "e" and moves the operator at the position i by "d".
#     """
#     if e.is_Mul:
#         if d == 1:
#             # e = a*b*c*d
#             a = Mul(*e.args[:i])
#             b = e.args[i]
#             c = e.args[i+1]
#             d = Mul(*e.args[i+2:])
#             if isinstance(b, Dagger) and not isinstance(c, Dagger):
#                 i, j = b.args[0].args[0], c.args[0]
#                 return a*c*b*d-a*KroneckerDelta(i, j)*d
#             elif not isinstance(b, Dagger) and isinstance(c, Dagger):
#                 i, j = b.args[0], c.args[0].args[0]
#                 return a*c*b*d-a*KroneckerDelta(i, j)*d
#             else:
#                 return a*c*b*d
#         elif d == -1:
#             # e = a*b*c*d
#             a = Mul(*e.args[:i-1])
#             b = e.args[i-1]
#             c = e.args[i]
#             d = Mul(*e.args[i+1:])
#             if isinstance(b, Dagger) and not isinstance(c, Dagger):
#                 i, j = b.args[0].args[0], c.args[0]
#                 return a*c*b*d-a*KroneckerDelta(i, j)*d
#             elif not isinstance(b, Dagger) and isinstance(c, Dagger):
#                 i, j = b.args[0], c.args[0].args[0]
#                 return a*c*b*d-a*KroneckerDelta(i, j)*d
#             else:
#                 return a*c*b*d
#         else:
#             if d > 1:
#                 while d >= 1:
#                     e = move(e, i, 1)
#                     d -= 1
#                     i += 1
#                 return e
#             elif d < -1:
#                 while d <= -1:
#                     e = move(e, i, -1)
#                     d += 1
#                     i -= 1
#                 return e
#     elif isinstance(e, Add):
#         a, b = e.as_two_terms()
#         return move(a, i, d) + move(b, i, d)
#     raise NotImplementedError()

class Commutator(Function):
    """
    The Commutator:  [A, B] = A*B - B*A

    The arguments are ordered according to .__cmp__()

    >>> from sympy import symbols
    >>> from sympy.physics.secondquant import Commutator
    >>> A, B = symbols('A,B', commutative=False)
    >>> Commutator(B, A)
    -Commutator(A, B)

    Evaluate the commutator with .doit()

    >>> comm = Commutator(A,B); comm
    Commutator(A, B)
    >>> comm.doit()
    A*B - B*A


    For two second quantization operators the commutator is evaluated
    immediately:

    >>> from sympy.physics.secondquant import Fd, F
    >>> a = symbols('a',above_fermi=True)
    >>> i = symbols('i',below_fermi=True)
    >>> p,q = symbols('p,q')

    >>> Commutator(Fd(a),Fd(i))
    2*NO(CreateFermion(a)*CreateFermion(i))

    But for more complicated expressions, the evaluation is triggered by
    a call to .doit()

    >>> comm = Commutator(Fd(p)*Fd(q),F(i)); comm
    Commutator(CreateFermion(p)*CreateFermion(q), AnnihilateFermion(i))
    >>> comm.doit(wicks=True)
    -KroneckerDelta(i, p)*CreateFermion(q) + KroneckerDelta(i, q)*CreateFermion(p)

    """

    is_commutative = False
    nargs = 2

    @classmethod
    def eval(cls, a,b):
        """
        The Commutator [A,B] is on canonical form if A < B


        """
        if not (a and b): return S.Zero
        if a == b: return S.Zero
        if a.is_commutative or b.is_commutative:
            return S.Zero

        #
        # [A+B,C]  ->  [A,C] + [B,C]
        #
        a = a.expand()
        if isinstance(a,Add):
            return Add(*[cls(term,b) for term in a.args])
        b = b.expand()
        if isinstance(b,Add):
            return Add(*[cls(a,term) for term in b.args])

        #
        # [xA,yB]  ->  xy*[A,B]
        #
        c_part = []
        nc_part = []
        nc_part2 = []
        if isinstance(a,Mul):
            c_part,nc_part = split_commutative_parts(a)
        if isinstance(b,Mul):
            c_part2,nc_part2 = split_commutative_parts(b)
            c_part.extend(c_part2)
        if c_part:
            a = nc_part or [a]
            b = nc_part2 or [b]
            return Mul(*c_part)*cls(Mul(*a),Mul(*b))


        #
        # single second quantization operators
        #
        if isinstance(a, BosonicOperator) and isinstance(b, BosonicOperator):
            if isinstance(b,CreateBoson) and isinstance(a,AnnihilateBoson):
                return KroneckerDelta(a.state,b.state)
            if isinstance(a,CreateBoson) and isinstance(b,AnnihilateBoson):
                return S.NegativeOne*KroneckerDelta(a.state,b.state)
            else:
                return S.Zero
        if isinstance(a, FermionicOperator) and isinstance(b, FermionicOperator):
            return wicks(a*b)- wicks(b*a)

        #
        # Canonical ordering of arguments
        #
        if a > b:
            return S.NegativeOne*cls(b, a)


    def doit(self,**hints):
        a = self.args[0]
        b = self.args[1]

        if hints.get("wicks"):
            a = a.doit(**hints)
            b = b.doit(**hints)
            try:
                return wicks(a*b) - wicks(b*a)
            except ContractionAppliesOnlyToFermions:
                pass
            except WicksTheoremDoesNotApply:
                pass

        return (a*b - b*a).doit(**hints)


    def __repr__(self):
        return "Commutator(%s,%s)" %(self.args[0],self.args[1])

    def __str__(self):
        return "[%s,%s]" %(self.args[0],self.args[1])

    def _latex(self,printer):
        return "\\left[%s,%s\\right]"%tuple([
            printer._print(arg) for arg in self.args])



class NO(Expr):
    """
    This Object is used to represent normal ordering brackets.

    i.e.  {abcd}  sometimes written  :abcd:

    Applying the function NO(arg) to an argument means that all operators in
    the argument will be assumed to anticommute, and have vanishing
    contractions.  This allows an immediate reordering to canonical form
    upon object creation.

    >>> from sympy import symbols
    >>> from sympy.physics.secondquant import NO, F, Fd
    >>> p,q = symbols('p,q')
    >>> NO(Fd(p)*F(q))
    NO(CreateFermion(p)*AnnihilateFermion(q))
    >>> NO(F(q)*Fd(p))
    -NO(CreateFermion(p)*AnnihilateFermion(q))


    Note:
    If you want to generate a normal ordered equivalent of an expression, you
    should use the function wicks().  This class only indicates that all
    operators inside the brackets anticommute, and have vanishing contractions.
    Nothing more, nothing less.

    """
    nargs = 1
    is_commutative = False


    def __new__(cls,arg):
        """
        Use anticommutation to get canonical form of operators.

        Employ associativity of normal ordered product: {ab{cd}} = {abcd}
        but note that {ab}{cd} /= {abcd}

        We also employ distributivity: {ab + cd} = {ab} + {cd}

        Canonical form also implies expand() {ab(c+d)} = {abc} + {abd}

        """

        # {ab + cd} = {ab} + {cd}
        arg = sympify(arg)
        arg = arg.expand()
        if arg.is_Add:
            return Add(*[ cls(term) for term in arg.args])

        if arg.is_Mul:

            # take coefficient outside of normal ordering brackets
            c_part, seq = split_commutative_parts(arg)
            if c_part:
                coeff = Mul(*c_part)
                if not seq:
                    return coeff
            else:
                coeff = S.One


            # {ab{cd}} = {abcd}
            newseq = []
            foundit = False
            for fac in seq:
                if isinstance(fac,NO):
                    newseq.extend(fac.args)
                    foundit = True
                else:
                    newseq.append(fac)
            if foundit:
                return coeff*cls(Mul(*newseq))

            # We assume that the user don't mix B and F operators
            if isinstance(seq[0], BosonicOperator):
                raise NotImplementedError

            try:
                newseq,sign = _sort_anticommuting_fermions(seq)
            except ViolationOfPauliPrinciple:
                return S.Zero

            if sign%2:
                return (S.NegativeOne*coeff)*cls(Mul(*newseq))
            elif sign:
                return coeff*cls(Mul(*newseq))
            else:
                pass #since sign==0, no permutations was necessary

            # if we couldn't do anything with Mul object, we just
            # mark it as normal ordered
            if coeff != S.One:
                return coeff*cls(Mul(*newseq))
            return Expr.__new__(cls, Mul(*newseq))

        if isinstance(arg,NO):
            return arg

        # if object was not Mul or Add, normal ordering does not apply
        return arg

    @property
    def has_q_creators(self):
        """
        Returns yes or no, fast

        Also, in case of yes, we indicate whether leftmost operator is a
        quasi creator above or below fermi.

        >>> from sympy import symbols
        >>> from sympy.physics.secondquant import NO, F, Fd

        >>> a = symbols('a',above_fermi=True)
        >>> i = symbols('i',below_fermi=True)
        >>> NO(Fd(a)*Fd(i)).has_q_creators
        1
        >>> NO(F(i)*F(a)).has_q_creators
        -1
        >>> NO(Fd(i)*F(a)).has_q_creators           #doctest: +SKIP
        0

        """
        return self.args[0].args[0].is_q_creator

    @property
    def has_q_annihilators(self):
        """
        Returns yes or no, fast

        Also, in case of yes, we indicate whether rightmost operator is an
        annihilator above or below fermi.

        >>> from sympy import symbols
        >>> from sympy.physics.secondquant import NO, F, Fd

        >>> a = symbols('a',above_fermi=True)
        >>> i = symbols('i',below_fermi=True)
        >>> NO(Fd(a)*Fd(i)).has_q_annihilators
        -1
        >>> NO(F(i)*F(a)).has_q_annihilators
        1
        >>> NO(Fd(a)*F(i)).has_q_annihilators        #doctest: +SKIP
        0

        """
        return self.args[0].args[-1].is_q_annihilator

    def doit(self, **kw_args):
        if kw_args.get("remove_brackets", True):
            return self._remove_brackets()
        else:
            return self.__new__(type(self),self.args[0].doit(**kw_args))

    def _remove_brackets(self):
        """
        Returns the sorted string without normal order brackets.

        The returned string have the property that no nonzero
        contractions exist.
        """

        # check if any creator is also an annihilator
        subslist=[]
        for i in self.iter_q_creators():
            if self[i].is_q_annihilator:
                assume = self[i].state.assumptions0

                # only operators with a dummy index can be split in two terms
                if isinstance(self[i].state, Dummy):

                    # create indices with fermi restriction
                    assume.pop("above_fermi", None)
                    assume["below_fermi"]=True
                    below = Dummy('i',**assume)
                    assume.pop("below_fermi", None)
                    assume["above_fermi"]=True
                    above = Dummy('a',**assume)

                    cls = type(self[i])
                    split = (
                            self[i].__new__(cls,below)
                            * KroneckerDelta(below,self[i].state)
                            + self[i].__new__(cls,above)
                            * KroneckerDelta(above,self[i].state)
                            )
                    subslist.append((self[i],split))
                else:
                    raise SubstitutionOfAmbigousOperatorFailed(self[i])
        if subslist:
            result = NO(self.subs(subslist))
            if isinstance(result, Add):
                return Add(*[term.doit() for term in result.args])
        else:
            return self.args[0]

    def _expand_operators(self):
        """
        Returns a sum of NO objects that contain no ambiguous q-operators.

        If an index q has range both above and below fermi, the operator F(q)
        is ambiguous in the sense that it can be both a q-creator and a q-annihilator.
        If q is dummy, it is assumed to be a summation variable and this method
        rewrites it into a sum of NO terms with unambiguous operators:

        {Fd(p)*F(q)} = {Fd(a)*F(b)} + {Fd(a)*F(i)} + {Fd(j)*F(b)} -{F(i)*Fd(j)}

        where a,b are above and i,j are below fermi level.
        """
        return NO(self._remove_brackets)


    def _eval_subs(self,old,new):
        if self == old:
            return new
        ops = self.args[0].args
        for i in range(len(ops)):
            if ops[i] == old:
                l1 = ops[:i]+(new,)+ops[i+1:]
                return self.__class__(Mul(*l1))
        return Expr._eval_subs(self,old,new)

    def __getitem__(self,i):
        if isinstance(i,slice):
            indices = i.indices(len(self))
            return [self.args[0].args[i] for i in range(*indices)]
        else:
            return self.args[0].args[i]

    def __len__(self):
        return len(self.args[0].args)

    def iter_q_annihilators(self):
        """
        Iterates over the annihilation operators.

        >>> from sympy import symbols, Dummy
        >>> i,j,k,l = symbols('i j k l', below_fermi=True)
        >>> p,q,r,s = symbols('p q r s', cls=Dummy)
        >>> a,b,c,d = symbols('a b c d', above_fermi=True)
        >>> from sympy.physics.secondquant import NO, F, Fd
        >>> no = NO(Fd(a)*F(i)*Fd(j)*F(b))

        >>> no.iter_q_creators()
        <generator object... at 0x...>
        >>> list(no.iter_q_creators())
        [0, 1]
        >>> list(no.iter_q_annihilators())
        [3, 2]

        """
        ops = self.args[0].args
        iter = range(len(ops)-1, -1, -1)
        for i in iter:
            if ops[i].is_q_annihilator:
                yield i
            else:
                break

    def iter_q_creators(self):
        """
        Iterates over the creation operators.

        >>> from sympy import symbols, Dummy
        >>> i,j,k,l = symbols('i j k l',below_fermi=True)
        >>> p,q,r,s = symbols('p q r s', cls=Dummy)
        >>> a,b,c,d = symbols('a b c d',above_fermi=True)
        >>> from sympy.physics.secondquant import NO, F, Fd
        >>> no = NO(Fd(a)*F(i)*Fd(j)*F(b))

        >>> no.iter_q_creators()
        <generator object... at 0x...>
        >>> list(no.iter_q_creators())
        [0, 1]
        >>> list(no.iter_q_annihilators())
        [3, 2]

        """

        ops = self.args[0].args
        iter = range(0, len(ops))
        for i in iter:
            if ops[i].is_q_creator:
                yield i
            else:
                break

    def get_subNO(self, i):
        """
        Returns a NO() without FermionicOperator at index i

        >>> from sympy import symbols
        >>> from sympy.physics.secondquant import F, NO
        >>> p,q,r = symbols('p,q,r')

        >>> NO(F(p)*F(q)*F(r)).get_subNO(1)  # doctest: +SKIP
        NO(AnnihilateFermion(p)*AnnihilateFermion(r))

        """
        arg0 = self.args[0] # it's a Mul by definition of how it's created
        mul = Mul._new_rawargs(arg0, Mul._new_rawargs(arg0, arg0.args[:i]),
                                     Mul._new_rawargs(arg0, arg0.args[i + 1:]))
        return NO(mul)

    def _latex(self,printer):
        return "\\left\\{%s\\right\\}"%printer._print(self.args[0])

    def __repr__(self):
        return "NO(%s)"%self.args[0]

    def __str__(self):
        return ":%s:" % self.args[0]


# @cacheit
def contraction(a,b):
    """
    Calculates contraction of Fermionic operators ab

    >>> from sympy import symbols
    >>> from sympy.physics.secondquant import F, Fd, contraction
    >>> p,q = symbols('p,q')
    >>> a,b = symbols('a,b', above_fermi=True)
    >>> i,j = symbols('i,j', below_fermi=True)

    A contraction is non-zero only if a quasi-creator is to the right of a
    quasi-annihilator:

    >>> contraction(F(a),Fd(b))
    KroneckerDelta(a, b)
    >>> contraction(Fd(i),F(j))
    KroneckerDelta(i, j)

    For general indices a non-zero result restricts the indices to below/above
    the fermi surface:

    >>> contraction(Fd(p),F(q))
    KroneckerDelta(p, q)*KroneckerDelta(q, _i)
    >>> contraction(F(p),Fd(q))
    KroneckerDelta(p, q)*KroneckerDelta(q, _a)

    Two creators or two annihilators always vanishes:

    >>> contraction(F(p),F(q))
    0
    >>> contraction(Fd(p),Fd(q))
    0

    """
    if isinstance(b,FermionicOperator) and isinstance(a,FermionicOperator):
        if isinstance(a,AnnihilateFermion) and isinstance(b,CreateFermion):
            if b.state.assumptions0.get("below_fermi"):
                return S.Zero
            if a.state.assumptions0.get("below_fermi"):
                return S.Zero
            if b.state.assumptions0.get("above_fermi"):
                return KroneckerDelta(a.state,b.state)
            if a.state.assumptions0.get("above_fermi"):
                return KroneckerDelta(a.state,b.state)

            return (KroneckerDelta(a.state,b.state)*
                    KroneckerDelta(b.state,Dummy('a',above_fermi=True)))
        if isinstance(b,AnnihilateFermion) and isinstance(a,CreateFermion):
            if b.state.assumptions0.get("above_fermi"):
                return S.Zero
            if a.state.assumptions0.get("above_fermi"):
                return S.Zero
            if b.state.assumptions0.get("below_fermi"):
                return KroneckerDelta(a.state,b.state)
            if a.state.assumptions0.get("below_fermi"):
                return KroneckerDelta(a.state,b.state)

            return (KroneckerDelta(a.state,b.state)*
                    KroneckerDelta(b.state,Dummy('i',below_fermi=True)))

        # vanish if 2xAnnihilator or 2xCreator
        return S.Zero

    else:
        #not fermion operators
        t = ( isinstance(i,FermionicOperator) for i in (a,b) )
        raise ContractionAppliesOnlyToFermions(*t)

def sqkey(sq_operator):
    """Generates key for canonical sorting of SQ operators"""
    return sq_operator._sortkey()

def _sort_anticommuting_fermions(string1, key=sqkey):
    """Sort fermionic operators to canonical order, assuming all pairs anticommute.

    Uses a bidirectional bubble sort.  Items in string1 are not referenced
    so in principle they may be any comparable objects.   The sorting depends on the
    operators '>' and '=='.

    If the Pauli principle is violated, an exception is raised.

    returns a tuple (sorted_str, sign)

    sorted_str -- list containing the sorted operators
    sign       -- int telling how many times the sign should be changed
                  (if sign==0 the string was already sorted)
    """

    verified = False
    sign = 0
    rng = list(range(len(string1)-1))
    rev = list(range(len(string1)-3,-1,-1))

    keys = list(map(key, string1))
    key_val = dict(list(zip(keys, string1)))

    while not verified:
        verified = True
        for i in rng:
            left = keys[i]
            right = keys[i+1]
            if left == right:
                raise ViolationOfPauliPrinciple([left,right])
            if left > right:
                verified = False
                keys[i:i+2] = [right, left]
                sign = sign+1
        if verified:
            break
        for i in rev:
            left = keys[i]
            right = keys[i+1]
            if left == right:
                raise ViolationOfPauliPrinciple([left,right])
            if left > right:
                verified = False
                keys[i:i+2] = [right, left]
                sign = sign+1
    string1 = [ key_val[k] for k in keys ]
    return (string1,sign)

def evaluate_deltas(e):
    """
    We evaluate KroneckerDelta symbols in the expression assuming Einstein summation.

    If one index is repeated it is summed over and in effect substituted with
    the other one. If both indices are repeated we substitute according to what
    is the preferred index.  this is determined by
    KroneckerDelta.preferred_index and KroneckerDelta.killable_index.

    In case there are no possible substitutions or if a substitution would
    imply a loss of information, nothing is done.

    In case an index appears in more than one KroneckerDelta, the resulting
    substitution depends on the order of the factors.  Since the ordering is platform
    dependent, the literal expression resulting from this function may be hard to
    predict.

    Examples:
    =========

    We assume that

    >>> from sympy import symbols, Function, Dummy
    >>> from sympy.physics.secondquant import evaluate_deltas, KroneckerDelta
    >>> i,j = symbols('i j', below_fermi=True, cls=Dummy)
    >>> a,b = symbols('a b', above_fermi=True, cls=Dummy)
    >>> p,q = symbols('p q', cls=Dummy)
    >>> f = Function('f')
    >>> t = Function('t')

    The order of preference for these indices according to KroneckerDelta is
    (a,b,i,j,p,q).

    Trivial cases:

    >>> evaluate_deltas(KroneckerDelta(i,j)*f(i))       # d_ij f(i) -> f(j)
    f(_j)
    >>> evaluate_deltas(KroneckerDelta(i,j)*f(j))       # d_ij f(j) -> f(i)
    f(_i)
    >>> evaluate_deltas(KroneckerDelta(i,p)*f(p))       # d_ip f(p) -> f(i)
    f(_i)
    >>> evaluate_deltas(KroneckerDelta(q,p)*f(p))       # d_qp f(p) -> f(q)
    f(_q)
    >>> evaluate_deltas(KroneckerDelta(q,p)*f(q))       # d_qp f(q) -> f(p)
    f(_p)

    More interesting cases:

    >>> evaluate_deltas(KroneckerDelta(i,p)*t(a,i)*f(p,q))
    f(_i, _q)*t(_a, _i)
    >>> evaluate_deltas(KroneckerDelta(a,p)*t(a,i)*f(p,q))
    f(_a, _q)*t(_a, _i)
    >>> evaluate_deltas(KroneckerDelta(p,q)*f(p,q))
    f(_p, _p)

    Finally, here are some cases where nothing is done, because that would
    imply a loss of information:

    >>> evaluate_deltas(KroneckerDelta(i,p)*f(q))
    f(_q)*KroneckerDelta(_i, _p)
    >>> evaluate_deltas(KroneckerDelta(i,p)*f(i))
    f(_i)*KroneckerDelta(_i, _p)
    """


    # We treat Deltas only in mul objects

    # for general function objects we don't evaluate KroneckerDeltas in arguments,
    # but here we hard code exceptions to this rule
    accepted_functions = (
            Add,
            )
    if isinstance(e, accepted_functions):
        return e.func(*[evaluate_deltas(arg) for arg in e.args])

    elif isinstance(e,Mul):
        # find all occurences of delta function and count each index present in
        # expression.
        deltas = []
        indices = {}
        for i in e.args:
            for s in i.atoms():
                if s in indices:
                    indices[s] += 1
                else:
                    indices[s] = 0  # geek counting simplifies logic below
            if isinstance(i, KroneckerDelta): deltas.append(i)

        for d in deltas:
            # If we do something, and there are more deltas, we should recurse
            # to treat the resulting expression properly
            if indices[d.killable_index]:
                e = e.subs(d.killable_index,d.preferred_index)
                if len(deltas)>1: return evaluate_deltas(e)
            elif indices[d.preferred_index] and d.indices_contain_equal_information:
                e = e.subs(d.preferred_index,d.killable_index)
                if len(deltas)>1: return evaluate_deltas(e)
            else:
                pass

        return e
    # nothing to do, maybe we hit a Symbol or a number
    else:
        return e


def substitute_dummies(expr, new_indices=False, pretty_indices={}):
    """
    Collect terms by substitution of dummy variables.

    This routine allows simplification of Add expressions containing terms
    which differ only due to dummy variables.

    The idea is to substitute all dummy variables consistently depending on
    the structure of the term.  For each term, we obtain a sequence of all
    dummy variables, where the order is determined by the index range, what
    factors the index belongs to and its position in each factor.  See
    _get_ordered_dummies() for more inforation about the sorting of dummies.
    The index sequence is then substituted consistently in each term.

    Examples
    --------

    >>> from sympy import symbols, Function, Dummy
    >>> from sympy.physics.secondquant import substitute_dummies
    >>> a,b,c,d = symbols('a b c d', above_fermi=True, cls=Dummy)
    >>> i,j = symbols('i j', below_fermi=True, cls=Dummy)
    >>> f = Function('f')

    >>> expr = f(a,b) + f(c,d); expr
    f(_a, _b) + f(_c, _d)

    Since a, b, c and d are equivalent summation indices, the expression can be
    simplified to a single term (for which the dummy indices are still summed over)

    >>> substitute_dummies(expr)
    2*f(_a, _b)


    Controlling output
    ------------------

    By default the dummy symbols that are already present in the expression
    will be reused in a different permuation.  However, if new_indices=True,
    new dummies will be generated and inserted.  The keyword 'pretty_indices'
    can be used to control this generation of new symbols.

    By default the new dummies will be generated on the form i_1, i_2, a_1,
    etc.  If you supply a dictionary with key:value pairs in the form:

        { index_group: string_of_letters }

    The letters will be used as labels for the new dummy symbols.  The
    index_groups must be one of 'above', 'below' or 'general'.

    >>> expr = f(a,b,i,j)
    >>> my_dummies = { 'above':'st','below':'uv' }
    >>> substitute_dummies(expr, new_indices=True, pretty_indices=my_dummies)
    f(_s, _t, _u, _v)

    If we run out of letters, or if there is no keyword for some index_group
    the default dummy generator will be used as a fallback:

    >>> p,q = symbols('p q', cls=Dummy)  # general indices
    >>> expr = f(p,q)
    >>> substitute_dummies(expr, new_indices=True, pretty_indices=my_dummies)
    f(_p_0, _p_1)

    """

    # setup the replacing dummies
    if new_indices:
        letters_above  = pretty_indices.get('above',"")
        letters_below  = pretty_indices.get('below',"")
        letters_general= pretty_indices.get('general',"")
        len_above  = len(letters_above)
        len_below  = len(letters_below)
        len_general= len(letters_general)

        def _i(number):
            try:
                return letters_below[number]
            except IndexError:
                return 'i_'+str(number-len_below)

        def _a(number):
            try:
                return letters_above[number]
            except IndexError:
                return 'a_'+str(number-len_above)

        def _p(number):
            try:
                return letters_general[number]
            except IndexError:
                return 'p_'+str(number-len_general)

    aboves = []
    belows = []
    generals = []

    dummies = expr.atoms(Dummy)
    if not new_indices:
        dummies = sorted(dummies)

    # generate lists with the dummies we will insert
    a = i = p = 0
    for d in dummies:
        assum = d.assumptions0

        if assum.get("above_fermi"):
            if new_indices: sym = _a(a); a +=1
            l1 = aboves
        elif assum.get("below_fermi"):
            if new_indices: sym = _i(i); i +=1
            l1 = belows
        else:
            if new_indices: sym = _p(p); p +=1
            l1 = generals

        if new_indices:
            l1.append(Dummy(sym, **assum))
        else:
            l1.append(d)


    expr = expr.expand()
    terms = Add.make_args(expr)
    new_terms = []
    for term in terms:
        i = iter(belows)
        a = iter(aboves)
        p = iter(generals)
        ordered  = _get_ordered_dummies(term)
        subsdict = {}
        for d in ordered:
            if d.assumptions0.get('below_fermi'):
                subsdict[d] = next(i)
            elif d.assumptions0.get('above_fermi'):
                subsdict[d] = next(a)
            else:
                subsdict[d] = next(p)
        subslist = []
        final_subs = []
        for k, v in subsdict.items():
            if k == v:
                continue
            if v in subsdict:
                # We check if the sequence of substitutions end quickly.  In
                # that case, we can avoid temporary symbols if we ensure the
                # correct substitution order.
                if subsdict[v] in subsdict:
                    # (x, y) -> (y, x),  we need a temporary variable
                    x = Dummy('x')
                    subslist.append((k, x))
                    final_subs.append((x, v))
                else:
                    # (x, y) -> (y, a),  x->y must be done last
                    # but before temporary variables are resolved
                    final_subs.insert(0, (k, v))
            else:
                subslist.append((k, v))
        subslist.extend(final_subs)
        new_terms.append(term.subs(subslist))
    return Add(*new_terms)

class KeyPrinter(StrPrinter):
    """Printer for which only equal objects are equal in print"""
    def _print_Dummy(self, expr):
        return "(%s_%i)" % (expr.name, expr.dummy_index)

def __kprint(expr):
    p = KeyPrinter()
    return p.doprint(expr)

def _get_ordered_dummies(mul, verbose = False):
    """Returns all dummies in the mul sorted in canonical order

    The purpose of the canonical ordering is that dummies can be substituted
    consistently accross terms with the result that equivalent terms can be
    simplified.

    It is not possible to determine if two terms are equivalent based solely on
    the dummy order.  However, a consistent substitution guided by the ordered
    dummies should lead to trivially (non-)equivalent terms, thereby revealing
    the equivalence.  This also means that if two terms have identical sequences of
    dummies, the (non-)equivalence should already be apparent.

    Strategy
    --------

    The canoncial order is given by an arbitrary sorting rule.  A sort key
    is determined for each dummy as a tuple that depends on all factors where
    the index is present.  The dummies are thereby sorted according to the
    contraction structure of the term, instead of sorting based solely on the
    dummy symbol itself.

    After all dummies in the term has been assigned a key, we check for identical
    keys, i.e. unorderable dummies.  If any are found, we call a specialized
    method, _determine_ambiguous(), that will determine a unique order based
    on recursive calls to _get_ordered_dummies().

    Key description
    ---------------

    A high level description of the sort key:

        1. Range of the dummy index
        2. Relation to external (non-dummy) indices
        3. Position of the index in the first factor
        4. Position of the index in the second factor

    The sort key is a tuple with the following components:

        1. A single character indicating the range of the dummy (above, below
           or general.)
        2. A list of strings with fully masked string representations of all
           factors where the dummy is present.  By masked, we mean that dummies
           are represented by a symbol to indicate either below fermi, above or
           general.  No other information is displayed about the dummies at
           this point.  The list is sorted stringwise.
        3. An integer number indicating the position of the index, in the first
           factor as sorted in 2.
        4. An integer number indicating the position of the index, in the second
           factor as sorted in 2.

    If a factor is either of type AntiSymmetricTensor or SqOperator, the index
    position in items 3 and 4 is indicated as 'upper' or 'lower' only.
    (Creation operators are considered upper and annihilation operators lower.)

    If the masked factors are identical, the two factors cannot be ordered
    unambiguously in item 2.  In this case, items 3, 4 are left out.  If several
    indices are contracted between the unorderable factors, it will be handled by
    _determine_ambiguous()


    """
    # setup dicts to avoid repeated calculations in key()
    args = Mul.make_args(mul)
    fac_dum = dict([ (fac, fac.atoms(Dummy)) for fac in args] )
    fac_repr = dict([ (fac, __kprint(fac)) for fac in args] )
    all_dums = list(reduce(
        lambda x, y: x | y, list(fac_dum.values()), set()))
    mask = {}
    for d in all_dums:
        if d.assumptions0.get('below_fermi'):
            mask[d] = '0'
        elif d.assumptions0.get('above_fermi'):
            mask[d] = '1'
        else:
            mask[d] = '2'
    dum_repr = dict([ (d, __kprint(d)) for d in all_dums ])

    def key(d):
        dumstruct = [ fac for fac in fac_dum if d in fac_dum[fac] ]
        other_dums = reduce(lambda x, y: x | y,
                [ fac_dum[fac] for fac in dumstruct ])
        fac = dumstruct[-1]
        if other_dums is fac_dum[fac]:
            other_dums = fac_dum[fac].copy()
        other_dums.remove(d)
        masked_facs = [ fac_repr[fac] for fac in dumstruct ]
        for d2 in other_dums:
            masked_facs = [ fac.replace(dum_repr[d2], mask[d2])
                    for fac in masked_facs ]
        all_masked = [ fac.replace(dum_repr[d], mask[d]) for fac in masked_facs ]
        masked_facs = dict(list(zip(dumstruct, masked_facs)))

        # dummies for which the ordering cannot be determined
        if len(set(all_masked)) < len(all_masked):
            all_masked.sort()
            return mask[d], tuple(all_masked) # positions are ambiguous

        # sort factors according to fully masked strings
        keydict = dict(list(zip(dumstruct, all_masked)))
        dumstruct.sort(key=lambda x: keydict[x])
        all_masked.sort()

        pos_val = []
        for fac in dumstruct:
            if isinstance(fac,AntiSymmetricTensor):
                if d in fac.upper:
                    pos_val.append('u')
                if d in fac.lower:
                    pos_val.append('l')
            elif isinstance(fac, Creator):
                pos_val.append('u')
            elif isinstance(fac, Annihilator):
                pos_val.append('l')
            elif isinstance(fac, NO):
                ops = [ op for op in fac if op.has(d) ]
                for op in ops:
                    if isinstance(op, Creator):
                        pos_val.append('u')
                    else:
                        pos_val.append('l')
            else:
                # fallback to position in string representation
                facpos = -1
                while 1:
                    facpos = masked_facs[fac].find(dum_repr[d], facpos+1)
                    if facpos == -1:
                        break
                    pos_val.append(facpos)
        return (mask[d], tuple(all_masked), pos_val[0], pos_val[-1])
    dumkey = dict(list(zip(all_dums, list(map(key, all_dums)))))
    result = sorted(all_dums, key=lambda x: dumkey[x])
    if len(set(dumkey.values())) < len(dumkey):
        # We have ambiguities
        unordered = {}
        for d, k in dumkey.items():
            if k in unordered:
                unordered[k].add(d)
            else:
                unordered[k] = set([d])
        for k in [ k for k in unordered if len(unordered[k]) < 2 ]:
            del unordered[k]

        unordered = [ unordered[k] for k in sorted(unordered) ]
        result = _determine_ambiguous(mul, result, unordered)
    return result

def _determine_ambiguous(term, ordered, ambiguous_groups):
    # We encountered a term for which the dummy substitution is ambiguous.
    # This happens for terms with 2 or more contractions between factors that
    # cannot be uniquely ordered independent of summation indices.  For
    # example:
    #
    # Sum(p, q) v^{p, .}_{q, .}v^{q, .}_{p, .}
    #
    # Assuming that the indices represented by . are dummies with the
    # same range, the factors cannot be ordered, and there is no
    # way to determine a consistent ordering of p and q.
    #
    # The strategy employed here, is to relabel all unambiguous dummies with
    # non-dummy symbols and call _get_ordered_dummies again.  This procedure is
    # applied to the entire term so there is a possibility that
    # _determine_ambiguous() is called again from a deeper recursion level.

    # break recursion if there are no ordered dummies
    all_ambiguous = set()
    for dummies in ambiguous_groups:
        all_ambiguous |= dummies
    all_ordered = set(ordered) - all_ambiguous
    if not all_ordered:
        # FIXME: If we arrive here, there are no ordered dummies. A method to
        # handle this needs to be implemented.  In order to return something
        # useful nevertheless, we choose arbitrarily the first dummy and
        # determine the rest from this one.  This method is dependent on the
        # actual dummy labels which violates an assumption for the canonization
        # procedure.  A better implementation is needed.
        group = [ d for d in ordered if d in ambiguous_groups[0] ]
        d = group[0]
        all_ordered.add(d)
        ambiguous_groups[0].remove(d)

    stored_counter = __symbol_factory.counter
    subslist = []
    for d in [ d for d in ordered if d in all_ordered ]:
        nondum = next(__symbol_factory)
        subslist.append((d, nondum))
    newterm = term.subs(subslist)
    neworder = _get_ordered_dummies(newterm)
    __symbol_factory.set_counter(stored_counter)

    # update ordered list with new information
    for group in ambiguous_groups:
        ordered_group = [ d for d in neworder if d in group ]
        ordered_group.reverse()
        result = []
        for d in ordered:
            if d in group:
                result.append(ordered_group.pop())
            else:
                result.append(d)
        ordered = result
    return ordered

class _SymbolFactory(object):
    def __init__(self, label):
        self._counter = 0
        self._label = label

    def set_counter(self, value):
        self._counter = value

    @property
    def counter(self):
        return self._counter

    def __next__(self):
        s = Symbol("%s%i" % (self._label, self._counter))
        self._counter += 1
        return s
__symbol_factory = _SymbolFactory('_]"]_') # most certainly a unique label


@cacheit
def _get_contractions(string1, keep_only_fully_contracted=False):
    """
    Uses recursion to find all contractions. -- Internal helper function --

    Will find nonzero contractions in string1 between indices given in
    leftrange and rightrange.

    returns Add-object with contracted terms.
    """

    # Should we store current level of contraction?
    if keep_only_fully_contracted and string1:
        result = []
    else:
        result = [NO(Mul(*string1))]

    for i in range(len(string1)-1):
        for j in range(i+1,len(string1)):

            c = contraction(string1[i],string1[j])

            if c:
                # print "found contraction",c

                sign = (j-i+1) %2
                if sign:
                    coeff = S.NegativeOne*c
                else:
                    coeff = c

                #
                #  Call next level of recursion
                #  ============================
                #
                # We now need to find more contractions among operators
                #
                # oplist = string1[:i]+ string1[i+1:j] + string1[j+1:]
                #
                # To prevent overcounting, we don't allow contractions
                # we have already encountered. i.e. contractions between
                #       string1[:i] <---> string1[i+1:j]
                # and   string1[:i] <---> string1[j+1:].
                #
                # This leaves the case:
                oplist = string1[i+1:j] + string1[j+1:]

                if oplist:

                    result.append(coeff*NO(
                        Mul(*string1[:i])*_get_contractions( oplist,
                            keep_only_fully_contracted=keep_only_fully_contracted)))

                else:
                    result.append(coeff*NO( Mul(*string1[:i])))


        if keep_only_fully_contracted:
            break   # next iteration over i leaves leftmost operator string1[0] uncontracted

    return Add(*result)


# @cacheit
def wicks(e, **kw_args):
    """
    Returns the normal ordered equivalent of an expression using Wicks Theorem.


    >>> from sympy import symbols, Function, Dummy
    >>> from sympy.physics.secondquant import wicks, F, Fd, NO
    >>> p,q,r = symbols('p,q,r')
    >>> wicks(Fd(p)*F(q))  # doctest: +SKIP
    KroneckerDelta(p, q)*KroneckerDelta(q, _i) + NO(CreateFermion(p)*AnnihilateFermion(q))

    By default, the expression is expanded:

    >>> wicks(F(p)*(F(q)+F(r))) # doctest: +SKIP
    NO(AnnihilateFermion(p)*AnnihilateFermion(q)) + NO(AnnihilateFermion(p)*AnnihilateFermion(r))

    With the keyword 'keep_only_fully_contracted=True', only fully contracted
    terms are returned.

    By request, the result can be simplified in the following order:
     -- KroneckerDelta functions are evaluated
     -- Dummy variables are substituted consistently across terms

    >>> p,q,r = symbols('p q r', cls=Dummy)
    >>> wicks(Fd(p)*(F(q)+F(r)), keep_only_fully_contracted=True) # doctest: +SKIP
    KroneckerDelta(_i, _q)*KroneckerDelta(_p, _q) + KroneckerDelta(_i, _r)*KroneckerDelta(_p, _r)

    """


    if not e:
        return S.Zero

    opts={
            'simplify_kronecker_deltas':False,
            'expand':True,
            'simplify_dummies':False,
            'keep_only_fully_contracted':False
            }
    opts.update(kw_args)


    # check if we are already normally ordered
    if isinstance(e,NO):
        if opts['keep_only_fully_contracted']:
            return S.Zero
        else:
            return e
    elif isinstance(e,FermionicOperator):
        if opts['keep_only_fully_contracted']:
            return S.Zero
        else:
            return e

    # break up any NO-objects, and evaluate commutators
    e = e.doit(wicks=True)

    # make sure we have only one term to consider
    e = e.expand()
    if isinstance(e, Add):
        if opts['simplify_dummies']:
            return substitute_dummies(Add(*[ wicks(term, **kw_args) for term in e.args]))
        else:
            return Add(*[ wicks(term, **kw_args) for term in e.args])


    # For Mul-objects we can actually do something
    if isinstance(e, Mul):

        # we dont want to mess around with commuting part of Mul
        # so we factorize it out before starting recursion
        c_part = []
        string1 = []
        for factor in e.args:
            if factor.is_commutative:
                c_part.append(factor)
            else:
                string1.append(factor)
        n = len(string1)


        # catch trivial cases
        if n == 0:
            result= e
        elif n==1:
            if opts['keep_only_fully_contracted']:
                return S.Zero
            else:
                result = e

        else: # non-trivial

            if isinstance(string1[0], BosonicOperator):
                raise NotImplementedError

            string1 = tuple(string1)

            # recursion over higher order contractions
            result = _get_contractions(string1,
                keep_only_fully_contracted=opts['keep_only_fully_contracted'] )
            result =  Mul(*c_part)*result

        if opts['expand']:
            result = result.expand()
        if opts['simplify_kronecker_deltas']:
            result = evaluate_deltas(result)

        return result

    # there was nothing to do
    return e

class PermutationOperator(Expr):
    """
    Represents the index permutation operator P(ij)

    P(ij)*f(i)*g(j) = f(i)*g(j) - f(j)*g(i)
    """
    is_commutative = True
    def __new__(cls, i,j):
        i,j = list(map(sympify,(i,j)))
        if (i>j):
            obj =  Basic.__new__(cls,j,i)
        else:
            obj =  Basic.__new__(cls,i,j)
        return obj



    def get_permuted(self,expr):
        """
        Returns -expr with permuted indices.

        >>> from sympy import symbols, Function
        >>> from sympy.physics.secondquant import PermutationOperator
        >>> p,q = symbols('p,q')
        >>> f = Function('f')
        >>> PermutationOperator(p,q).get_permuted(f(p,q))
        -f(q, p)

        """
        i = self.args[0]
        j = self.args[1]
        if expr.has(i) and expr.has(j):
            tmp = Dummy()
            expr = expr.subs(i,tmp)
            expr = expr.subs(j,i)
            expr = expr.subs(tmp,j)
            return S.NegativeOne*expr
        else:
            return expr

    def _latex(self, printer):
        return "P(%s%s)"%self.args



def simplify_index_permutations(expr, permutation_operators):
    """
    Performs simplification by introducing PermutationOperators where appropriate.

    Schematically:
        [abij] - [abji] - [baij] + [baji] ->  P(ab)*P(ij)*[abij]

    permutation_operators is a list of PermutationOperators to consider.

    If permutation_operators=[P(ab),P(ij)] we will try to introduce the
    permutation operators P(ij) and P(ab) in the expression.  If there are other
    possible simplifications, we ignore them.

    >>> from sympy import symbols, Function
    >>> from sympy.physics.secondquant import simplify_index_permutations
    >>> from sympy.physics.secondquant import PermutationOperator
    >>> p,q,r,s = symbols('p,q,r,s')
    >>> f = Function('f')
    >>> g = Function('g')

    >>> expr = f(p)*g(q) - f(q)*g(p); expr
    f(p)*g(q) - f(q)*g(p)
    >>> simplify_index_permutations(expr,[PermutationOperator(p,q)])
    f(p)*g(q)*PermutationOperator(p, q)

    >>> PermutList = [PermutationOperator(p,q),PermutationOperator(r,s)]
    >>> expr = f(p,r)*g(q,s) - f(q,r)*g(p,s) + f(q,s)*g(p,r) - f(p,s)*g(q,r)
    >>> simplify_index_permutations(expr,PermutList)
    f(p, r)*g(q, s)*PermutationOperator(p, q)*PermutationOperator(r, s)

    """

    def _get_indices(expr, ind):
        """
        Collects indices recursively in predictable order.
        """
        result = []
        for arg in expr.args:
            if arg in ind:
                result.append(arg)
            else:
                if arg.args:
                    result.extend(_get_indices(arg,ind))
        return result

    def _choose_one_to_keep(a,b,ind):
        # we keep the one where indices in ind are in order ind[0] < ind[1]
        if _get_indices(a,ind) < _get_indices(b,ind):
            return a
        else:
            return b


    expr = expr.expand()
    if isinstance(expr,Add):
        terms = set(expr.args)

        for P in permutation_operators:
            new_terms = set([])
            on_hold = set([])
            while terms:
                term = terms.pop()
                permuted = P.get_permuted(term)
                if permuted in terms | on_hold:
                    try:
                        terms.remove(permuted)
                    except KeyError:
                        on_hold.remove(permuted)
                    keep = _choose_one_to_keep(term, permuted, P.args)
                    new_terms.add(P*keep)
                else:

                    # Some terms must get a second chance because the permuted
                    # term may already have canonical dummy ordering.  Then
                    # substitute_dummies() does nothing.  However, the other
                    # term, if it exists, will be able to match with us.
                    permuted1 = permuted
                    permuted = substitute_dummies(permuted)
                    if permuted1 == permuted:
                        on_hold.add(term)
                    elif permuted in terms | on_hold:
                        try:
                            terms.remove(permuted)
                        except KeyError:
                            on_hold.remove(permuted)
                        keep = _choose_one_to_keep(term, permuted, P.args)
                        new_terms.add(P*keep)
                    else:
                        new_terms.add(term)
            terms = new_terms | on_hold
        return Add(*terms)
    return expr
