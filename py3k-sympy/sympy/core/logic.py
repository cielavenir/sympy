"""Logic expressions handling

NOTE
----

at present this is mainly needed for facts.py , feel free however to improve
this stuff for general purpose.
"""
from sympy.core.compatibility import iterable, cmp

def fuzzy_bool(x):
    """Return True, False or None according to x.

    Whereas bool(x) returns True or False, fuzzy_bool allows
    for the None value.
    """
    if x is None:
        return None
    return bool(x)

def fuzzy_and(*args):
    """Return True (all True), False (any False) or None.

    If `a` is an iterable it must have more than one element."""

    if (len(args) == 1 and iterable(args[0]) or
        len(args) > 2):
        if len(args) == 1:
            args = args[0]
        rv = True
        i = 0
        for ai in args:
            ai = fuzzy_bool(ai)
            if ai is False:
                return False
            if rv: # this will stop updating if a None is ever trapped
                rv = ai
            i += 1
        if i < 2:
            raise ValueError('iterables must have 2 or more elements')
        return rv

    a, b = [fuzzy_bool(i) for i in args]
    if a is True and b is True:
        return True
    elif a is False or b is False:
        return False

def fuzzy_not(v):
    """'not' in fuzzy logic"""
    if v is None:
        return v
    else:
        return not v


def name_not(k):
    """negate a name

       >>> from sympy.core.logic import name_not
       >>> name_not('zero')
       '!zero'

       >>> name_not('!zero')
       'zero'

    """
    if k[:1] != '!':
        return '!'+k
    else:
        return k[1:]


class Logic(object):
    """Logical expression"""

    __slots__ = ['args']

    # {} 'op' -> LogicClass
    op_2class = {}


    def __new__(cls, args):
        obj = object.__new__(cls)
        obj.args = tuple(args)

        # XXX do we need this:
        #print 'L: %s' % (obj.args,)
        assert not isinstance(obj.args[0], tuple)

        return obj


    def __hash__(self):
        return hash( (type(self).__name__, self.args) )


    def __eq__(a, b):
        if not isinstance(b, type(a)):
            return False
        else:
            return a.args == b.args

    def __ne__(a, b):
        if not isinstance(b, type(a)):
            return True
        else:
            return a.args != b.args

    def __lt__(cls, other):
        if cls.__cmp__(other) == -1:
            return True
        return False


    def __cmp__(a, b):
        if type(a) is not type(b):
            return cmp( str(type(a)), str(type(b)) )

        else:
            return cmp(a.args, b.args)




    # XXX later, we may want to change how expressions are printed
    def __str__(self):
        return '%s(%s)' % (self.op, ', '.join(str(a) for a in self.args))

    # XXX this is not good ...
    __repr__ = __str__


    @staticmethod
    def fromstring(text):
        """Logic from string

           e.g.

           !a & !b | c
        """
        # XXX this is not general, but good enough
        terms = text.split()

        lexpr   = None  # current logical expression
        schedop = None  # scheduled operation

        while True:
            # pop next term and exit loop if there is no terms left
            try:
                term = terms.pop(0)
            except IndexError:
                break

            # operation symbol
            if term in '&|':
                if schedop is not None:
                    raise ValueError('double op forbidden: "%s %s"' % (term, schedop))

                if lexpr is None:
                    raise ValueError('%s cannot be in the beginning of expression' % term)

                schedop = term
                continue


            # already scheduled operation, e.g. '&'
            if schedop:
                lexpr   = Logic.op_2class[schedop] ( *(lexpr, term) )
                schedop = None
                continue

            # this should be atom
            if lexpr is not None:
                raise ValueError('missing op between "%s" and "%s"' % (lexpr, term))

            lexpr = term


        # let's check that we ended up in correct state
        if schedop is not None:
            raise ValueError('premature end-of-expression in "%s"' % text)
        if lexpr is None:
            raise ValueError('"%s" is empty' % text)

        # everything looks good now
        return lexpr


# XXX better name?
class AndOr_Base(Logic):

    __slots__ = []

    def __new__(cls, *args):
        if len(args) == 0:
            raise TypeError('%s requires at least one argument' % cls.__name__)

        # process bool args early
        bargs = []

        for a in args:
            # &(F, ...) -> F
            # |(T, ...) -> T
            if a == cls.op_x_notx:
                return a

            # &(T, ...) -> &(...)
            # |(F, ...) -> |(...)
            elif a == (not cls.op_x_notx):
                continue    # skip this argument


            bargs.append(a)


        args = bargs

        # &(a, !a) -> F
        # |(a, !a) -> T
        # XXX suboptinal
        for a in args:
            if Not(a) in args:
                return cls.op_x_notx

        args = cls.flatten(args)

        # canonicalize arguments
        # XXX do we always need this?
        # NB: this is needed to reduce number of &-nodes in beta-network
        args = sorted(args, key=hash)

        # now let's kill duplicate arguments, e.g. &(a,a,b) -> &(a,b)
        prev = None
        uargs= []
        for a in args:
            if a != prev:
                uargs.append(a)
                prev = a

        args = uargs

        # &(a) -> a
        # |(a) -> a
        if len(args) == 1:
            return args[0]

        # when we are at this stage, it means that _all_ arguments were T/F and
        # all arguments were accepted as "let's see what follows next", so at
        # _this_ point the rule is:
        # |()  -> F  (*not* T)
        # &()  -> T  (*not* F)
        elif len(args) == 0:
            return not cls.op_x_notx

        return Logic.__new__(cls, args)


    @classmethod
    def flatten(cls, args):
        # quick-n-dirty flattening for And and Or
        args_queue = list(args)
        res = []

        while True:

            try:
                arg = args_queue.pop(0)
            except IndexError:
                break

            if isinstance(arg, Logic):
                if arg.op == cls.op:
                    #print 'flattening...', fargs, i, arg.args
                    args_queue.extend( arg.args )
                    continue


            # another op -- leave it as is
            res.append( arg )

        args = tuple(res)
        return args

expand_lvl=0

class And(AndOr_Base):
    op = '&'
    op_x_notx = False

    __slots__ = []

    def _eval_propagate_not(self):
        # !(a&b&c ...) == !a | !b | !c ...
        return Or( *[Not(a) for a in self.args] )


    # (a|b|...) & c == (a&c) | (b&c) | ...
    def expand(self):

        # first locate Or
        for i in range(len(self.args)):
            arg = self.args[i]
            if isinstance(arg, Or):
                arest = self.args[:i] + self.args[i+1:]

                orterms = [And( *(arest + (a,)) ) for a in arg.args]
                for j in range(len(orterms)):
                    if isinstance(orterms[j], Logic):
                        orterms[j] = orterms[j].expand()

                res = Or(*orterms)
                return res

        else:
            return self

    def dbg_expand(self):
        global expand_lvl
        print('%sexpand %s' % (' '*expand_lvl, self))

        expand_lvl += 1
        try:
            return self.old_expand()
        finally:
            expand_lvl -= 1


    #old_expand = expand
    #expand = dbg_expand

class Or(AndOr_Base):
    op = '|'
    op_x_notx = True

    __slots__ = []

    def _eval_propagate_not(self):
        # !(a|b|c ...) == !a & !b & !c ...
        return And( *[Not(a) for a in self.args] )

class Not(Logic):
    op = '!'

    __slots__ = []

    def __new__(cls, arg):
        if isinstance(arg, str):
            return name_not(arg)

        elif isinstance(arg, bool):
            return not arg

        elif isinstance(arg, Logic):
            # XXX this is a hack to expand right from the beginning
            arg = arg._eval_propagate_not()
            return arg

            obj = Logic.__new__(cls, (arg,))
            return obj

        else:
            raise ValueError('Not: unknown argument %r' % (arg,))





Logic.op_2class['&'] = And
Logic.op_2class['|'] = Or
Logic.op_2class['!'] = Not
