"""Inference in propositional logic"""
from sympy.logic.boolalg import And, Or, Not, Implies, Equivalent, \
    conjuncts, to_cnf
from sympy.core.basic import C
from sympy.core.sympify import sympify

def literal_symbol(literal):
    """The symbol in this literal (without the negation).
    >>> from sympy import Symbol
    >>> from sympy.abc import A
    >>> from sympy.logic.inference import literal_symbol
    >>> literal_symbol(A)
    A
    >>> literal_symbol(~A)
    A

    """
    if literal.func is Not:
        return literal.args[0]
    else:
        return literal

def satisfiable(expr, algorithm="dpll2"):
    """Check satisfiability of a propositional sentence.
    Returns a model when it succeeds

    Examples

    >>> from sympy.abc import A, B
    >>> from sympy.logic.inference import satisfiable
    >>> satisfiable(A & ~B)
    {A: True, B: False}
    >>> satisfiable(A & ~A)
    False

    """
    expr = to_cnf(expr)
    if algorithm == "dpll":
        from sympy.logic.algorithms.dpll import dpll_satisfiable
        return dpll_satisfiable(expr)
    elif algorithm == "dpll2":
        from sympy.logic.algorithms.dpll2 import dpll_satisfiable
        return dpll_satisfiable(expr)
    raise NotImplementedError

def pl_true(expr, model={}):
    """Return True if the propositional logic expression is true in the model,
    and False if it is false. If the model does not specify the value for
    every proposition, this may return None to indicate 'not obvious';
    this may happen even when the expression is tautological.

    The model is implemented as a dict containing the pair symbol, boolean value.

    Examples:
    >>> from sympy.abc import A, B
    >>> from sympy.logic.inference import pl_true
    >>> pl_true( A & B, {A: True, B : True})
    True

    """

    if isinstance(expr, bool):
        return expr

    expr = sympify(expr)
    if expr.is_Atom:
        return model.get(expr)

    args = expr.args
    if expr.func is Not:
        p = pl_true(args[0], model)
        if p is None: return None
        else: return not p
    elif expr.func is Or:
        result = False
        for arg in args:
            p = pl_true(arg, model)
            if p == True: return True
            if p == None: result = None
        return result
    elif expr.func is And:
        result = True
        for arg in args:
            p = pl_true(arg, model)
            if p == False: return False
            if p == None: result = None
        return result

    elif expr.func is Implies:
        p, q = args
        return pl_true(Or(Not(p), q), model)

    elif expr.func is Equivalent:
        p, q = args
        pt = pl_true(p, model)
        if pt == None:
            return None
        qt = pl_true(q, model)
        if qt == None:
            return None
        return pt == qt
    else:
        raise ValueError("Illegal operator in logic expression" + str(expr))


class KB(object):
    """Base class for all knowledge bases"""
    def __init__(self, sentence=None):
        self.clauses = []
        if sentence:
            self.tell(sentence)

    def tell(self, sentence):
        raise NotImplementedError

    def ask(self, query):
        raise NotImplementedError

    def retract(self, sentence):
        raise NotImplementedError


class PropKB(KB):
    "A KB for Propositional Logic.  Inefficient, with no indexing."

    def tell(self, sentence):
        "Add the sentence's clauses to the KB"
        for c in conjuncts(to_cnf(sentence)):
            if not c in self.clauses: self.clauses.append(c)

    def ask(self, query):
        """TODO: examples"""
        if len(self.clauses) == 0: return False
        from sympy.logic.algorithms.dpll import dpll
        query_conjuncts = self.clauses[:]
        query_conjuncts.extend(conjuncts(to_cnf(query)))
        s = set()
        for q in query_conjuncts:
            s = s.union(q.atoms(C.Symbol))
        return bool(dpll(query_conjuncts, list(s), {}))

    def retract(self, sentence):
        "Remove the sentence's clauses from the KB"
        for c in conjuncts(to_cnf(sentence)):
            if c in self.clauses:
                self.clauses.remove(c)
