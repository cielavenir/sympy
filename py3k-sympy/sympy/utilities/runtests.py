"""
This is our testing framework.

Goals:

* it should be compatible with py.test and operate very similarly (or
identically)
* doesn't require any external dependencies
* preferably all the functionality should be in this file only
* no magic, just import the test file and execute the test functions, that's it
* portable

"""
import os
import sys
import inspect
import traceback
import pdb
import re
import linecache
from fnmatch import fnmatch
from timeit import default_timer as clock
import doctest as pdoctest # avoid clashing with our doctest() function
from doctest import DocTestFinder, DocTestRunner
import re as pre
import random

# Use sys.stdout encoding for ouput.
# This was only added to Python's doctest in Python 2.6, so we must duplicate
# it here to make utf8 files work in Python 2.5.
pdoctest._encoding = getattr(sys.__stdout__, 'encoding', None) or 'utf-8'

def _indent(s, indent=4):
    """
    Add the given number of space characters to the beginning of
    every non-blank line in `s`, and return the result.
    If the string `s` is Unicode, it is encoded using the stdout
    encoding and the `backslashreplace` error handler.
    """
    if isinstance(s, str):
        s = s.encode(pdoctest._encoding, 'backslashreplace')
    # This regexp matches the start of non-blank lines:
    return re.sub('(?m)^(?!$)', indent*' ', s)

pdoctest._indent = _indent

def sys_normcase(f):
    if sys_case_insensitive:
        return f.lower()
    return f

def convert_to_native_paths(lst):
    """
    Converts a list of '/' separated paths into a list of
    native (os.sep separated) paths and converts to lowercase
    if the system is case insensitive.
    """
    newlst = []
    for i, rv in enumerate(lst):
        rv = os.path.join(*rv.split("/"))
        # on windows the slash after the colon is dropped
        if sys.platform == "win32":
            pos = rv.find(':')
            if pos != -1:
                if rv[pos+1] != '\\':
                    rv = rv[:pos+1] + '\\' + rv[pos+1:]
        newlst.append(sys_normcase(rv))
    return newlst

def get_sympy_dir():
    """
    Returns the root sympy directory and set the global value
    indicating whether the system is case sensitive or not.
    """
    global sys_case_insensitive

    this_file = os.path.abspath(__file__)
    sympy_dir = os.path.join(os.path.dirname(this_file), "..", "..")
    sympy_dir = os.path.normpath(sympy_dir)
    sys_case_insensitive = (os.path.isdir(sympy_dir) and
                        os.path.isdir(sympy_dir.lower()) and
                        os.path.isdir(sympy_dir.upper()))
    return sys_normcase(sympy_dir)

def isgeneratorfunction(object):
    """
    Return true if the object is a user-defined generator function.

    Generator function objects provides same attributes as functions.

    See isfunction.__doc__ for attributes listing.

    Adapted from Python 2.6.
    """
    CO_GENERATOR = 0x20
    if (inspect.isfunction(object) or inspect.ismethod(object)) and \
        object.__code__.co_flags & CO_GENERATOR:
        return True
    return False

def setup_pprint():
    from sympy import pprint_use_unicode, init_printing

    # force pprint to be in ascii mode in doctests
    pprint_use_unicode(False)

    # hook our nice, hash-stable strprinter
    init_printing(pretty_print=False)

def test(*paths, **kwargs):
    """
    Run all tests in test_*.py files which match any of the given
    strings in `paths` or all tests if paths=[].

    Notes:
       o if sort=False, tests are run in random order (not default).
       o paths can be entered in native system format or in unix,
         forward-slash format.

    Examples:

    >> import sympy

    Run all tests:
    >> sympy.test()

    Run one file:
    >> sympy.test("sympy/core/tests/test_basic.py")
    >> sympy.test("_basic")

    Run all tests in sympy/functions/ and some particular file:
    >> sympy.test("sympy/core/tests/test_basic.py", "sympy/functions")

    Run all tests in sympy/core and sympy/utilities:
    >> sympy.test("/core", "/util")

    Run specific test from a file:
    >> sympy.test("sympy/core/tests/test_basic.py", kw="test_equality")

    Run the tests with verbose mode on:
    >> sympy.test(verbose=True)

    Don't sort the test output:
    >> sympy.test(sort=False)

    Turn on post-mortem pdb:
    >> sympy.test(pdb=True)

    Turn off colors:
    >> sympy.test(colors=False)

    The traceback verboseness can be set to "short" or "no" (default is "short")
    >> sympy.test(tb='no')

    """
    verbose = kwargs.get("verbose", False)
    tb = kwargs.get("tb", "short")
    kw = kwargs.get("kw", "")
    post_mortem = kwargs.get("pdb", False)
    colors = kwargs.get("colors", True)
    sort = kwargs.get("sort", True)
    seed = kwargs.get("seed", None)
    if seed is None:
        seed = random.randrange(100000000)
    r = PyTestReporter(verbose, tb, colors)
    t = SymPyTests(r, kw, post_mortem, seed)

    # Disable warnings for external modules
    import sympy.external
    sympy.external.importtools.WARN_OLD_VERSION = False
    sympy.external.importtools.WARN_NOT_INSTALLED = False

    test_files = t.get_test_files('sympy')
    if len(paths) == 0:
        t._testfiles.extend(test_files)
    else:
        paths = convert_to_native_paths(paths)
        matched = []
        for f in test_files:
            basename = os.path.basename(f)
            for p in paths:
                if p in f or fnmatch(basename, p):
                    matched.append(f)
                    break
        t._testfiles.extend(matched)

    return t.test(sort=sort)

def doctest(*paths, **kwargs):
    """
    Runs doctests in all *py files in the sympy directory which match
    any of the given strings in `paths` or all tests if paths=[].

    Note:
       o paths can be entered in native system format or in unix,
         forward-slash format.
       o files that are on the blacklist can be tested by providing
         their path; they are only excluded if no paths are given.

    Examples:

    >> import sympy

    Run all tests:
    >> sympy.doctest()

    Run one file:
    >> sympy.doctest("sympy/core/basic.py")
    >> sympy.doctest("polynomial.txt")

    Run all tests in sympy/functions/ and some particular file:
    >> sympy.doctest("/functions", "basic.py")

    Run any file having polynomial in its name, doc/src/modules/polynomial.txt,
    sympy\functions\special\polynomials.py, and sympy\polys\polynomial.py:
    >> sympy.doctest("polynomial")
    """
    normal = kwargs.get("normal", False)
    verbose = kwargs.get("verbose", False)
    blacklist = kwargs.get("blacklist", [])
    blacklist.extend([
                    "doc/src/modules/mpmath", # needs to be fixed upstream
                    "sympy/mpmath", # needs to be fixed upstream
                    "doc/src/modules/plotting.txt", # generates live plots
                    "sympy/plotting", # generates live plots
                    "sympy/utilities/compilef.py", # needs tcc
                    "sympy/utilities/autowrap.py", # needs installed compiler
                    "sympy/galgebra/GA.py", # needs numpy
                    "sympy/galgebra/latex_ex.py", # needs numpy
                    "sympy/conftest.py", # needs py.test
                    "sympy/utilities/benchmarking.py", # needs py.test
                    ])
    blacklist = convert_to_native_paths(blacklist)

    # Disable warnings for external modules
    import sympy.external
    sympy.external.importtools.WARN_OLD_VERSION = False
    sympy.external.importtools.WARN_NOT_INSTALLED = False

    r = PyTestReporter(verbose)
    t = SymPyDocTests(r, normal)

    test_files = t.get_test_files('sympy')
    not_blacklisted = [f for f in test_files
                         if not any(b in f for b in blacklist)]
    if len(paths) == 0:
        t._testfiles.extend(not_blacklisted)
    else:
        # take only what was requested...but not blacklisted items
        # and allow for partial match anywhere or fnmatch of name
        paths = convert_to_native_paths(paths)
        matched = []
        for f in not_blacklisted:
            basename = os.path.basename(f)
            for p in paths:
                if p in f or fnmatch(basename, p):
                    matched.append(f)
                    break
        t._testfiles.extend(matched)

    # run the tests and record the result for this *py portion of the tests
    if t._testfiles:
        failed = not t.test()
    else:
        failed = False

    # test *txt files only if we are running python newer than 2.4
    if sys.version_info[:2] > (2,4):

        # N.B.
        # --------------------------------------------------------------------
        # Here we test *.txt files at or below doc/src. Code from these must
        # be self supporting in terms of imports since there is no importing
        # of necessary modules by doctest.testfile. If you try to pass *.py
        # files through this they might fail because they will lack the needed
        # imports and smarter parsing that can be done with source code.
        #
        test_files = t.get_test_files('doc/src', '*.txt', init_only=False)
        test_files.sort()

        not_blacklisted = [f for f in test_files
                             if not any(b in f for b in blacklist)]

        if len(paths) == 0:
            matched = not_blacklisted
        else:
            # Take only what was requested as long as it's not on the blacklist.
            # Paths were already made native in *py tests so don't repeat here.
            # There's no chance of having a *py file slip through since we
            # only have *txt files in test_files.
            matched =  []
            for f in not_blacklisted:
                basename = os.path.basename(f)
                for p in paths:
                    if p in f or fnmatch(basename, p):
                        matched.append(f)
                        break

        setup_pprint()
        first_report = True
        for txt_file in matched:
            if not os.path.isfile(txt_file):
                continue
            old_displayhook = sys.displayhook
            try:
                # out = pdoctest.testfile(txt_file, module_relative=False, encoding='utf-8',
                #    optionflags=pdoctest.ELLIPSIS | pdoctest.NORMALIZE_WHITESPACE)
                out = sympytestfile(txt_file, module_relative=False, encoding='utf-8',
                    optionflags=pdoctest.ELLIPSIS | pdoctest.NORMALIZE_WHITESPACE)
            finally:
                # make sure we return to the original displayhook in case some
                # doctest has changed that
                sys.displayhook = old_displayhook

            txtfailed, tested = out
            if tested:
                failed = txtfailed or failed
                if first_report:
                    first_report = False
                    msg = 'txt doctests start'
                    lhead = '='*((80 - len(msg))//2 - 1)
                    rhead = '='*(79 - len(msg) - len(lhead) - 1)
                    print(' '.join([lhead, msg, rhead]))
                    print()
                # use as the id, everything past the first 'sympy'
                file_id = txt_file[txt_file.find('sympy') + len('sympy') + 1:]
                print(file_id, end=' ') # get at least the name out so it is know who is being tested
                wid = 80 - len(file_id) - 1 #update width
                test_file = '[%s]' % (tested)
                report = '[%s]' % (txtfailed or 'OK')
                print(''.join([test_file,' '*(wid-len(test_file)-len(report)), report]))

        # the doctests for *py will have printed this message already if there was
        # a failure, so now only print it if there was intervening reporting by
        # testing the *txt as evidenced by first_report no longer being True.
        if not first_report and failed:
            print()
            print("DO *NOT* COMMIT!")
    return not failed

# The Python 2.5 doctest runner uses a tuple, but in 2.6+, it uses a namedtuple
# (which doesn't exist in 2.5-)
if sys.version_info[:2] > (2,5):
    from collections import namedtuple
    SymPyTestResults = namedtuple('TestResults', 'failed attempted')
else:
    SymPyTestResults = lambda a, b: (a, b)

def sympytestfile(filename, module_relative=True, name=None, package=None,
             globs=None, verbose=None, report=True, optionflags=0,
             extraglobs=None, raise_on_error=False,
             parser=pdoctest.DocTestParser(), encoding=None):
    """
    Test examples in the given file.  Return (#failures, #tests).

    Optional keyword arg "module_relative" specifies how filenames
    should be interpreted:

      - If "module_relative" is True (the default), then "filename"
         specifies a module-relative path.  By default, this path is
         relative to the calling module's directory; but if the
         "package" argument is specified, then it is relative to that
         package.  To ensure os-independence, "filename" should use
         "/" characters to separate path segments, and should not
         be an absolute path (i.e., it may not begin with "/").

      - If "module_relative" is False, then "filename" specifies an
        os-specific path.  The path may be absolute or relative (to
        the current working directory).

    Optional keyword arg "name" gives the name of the test; by default
    use the file's basename.

    Optional keyword argument "package" is a Python package or the
    name of a Python package whose directory should be used as the
    base directory for a module relative filename.  If no package is
    specified, then the calling module's directory is used as the base
    directory for module relative filenames.  It is an error to
    specify "package" if "module_relative" is False.

    Optional keyword arg "globs" gives a dict to be used as the globals
    when executing examples; by default, use {}.  A copy of this dict
    is actually used for each docstring, so that each docstring's
    examples start with a clean slate.

    Optional keyword arg "extraglobs" gives a dictionary that should be
    merged into the globals that are used to execute examples.  By
    default, no extra globals are used.

    Optional keyword arg "verbose" prints lots of stuff if true, prints
    only failures if false; by default, it's true iff "-v" is in sys.argv.

    Optional keyword arg "report" prints a summary at the end when true,
    else prints nothing at the end.  In verbose mode, the summary is
    detailed, else very brief (in fact, empty if all tests passed).

    Optional keyword arg "optionflags" or's together module constants,
    and defaults to 0.  Possible values (see the docs for details):

        DONT_ACCEPT_TRUE_FOR_1
        DONT_ACCEPT_BLANKLINE
        NORMALIZE_WHITESPACE
        ELLIPSIS
        SKIP
        IGNORE_EXCEPTION_DETAIL
        REPORT_UDIFF
        REPORT_CDIFF
        REPORT_NDIFF
        REPORT_ONLY_FIRST_FAILURE

    Optional keyword arg "raise_on_error" raises an exception on the
    first unexpected exception or failure. This allows failures to be
    post-mortem debugged.

    Optional keyword arg "parser" specifies a DocTestParser (or
    subclass) that should be used to extract tests from the files.

    Optional keyword arg "encoding" specifies an encoding that should
    be used to convert the file to unicode.

    Advanced tomfoolery:  testmod runs methods of a local instance of
    class doctest.Tester, then merges the results into (or creates)
    global Tester instance doctest.master.  Methods of doctest.master
    can be called directly too, if you want to do something unusual.
    Passing report=0 to testmod is especially useful then, to delay
    displaying a summary.  Invoke doctest.master.summarize(verbose)
    when you're done fiddling.
    """
    if package and not module_relative:
        raise ValueError("Package may only be specified for module-"
                         "relative paths.")

    # Relativize the path
    text, filename = pdoctest._load_testfile(filename, package, module_relative)

    # If no name was given, then use the file's name.
    if name is None:
        name = os.path.basename(filename)

    # Assemble the globals.
    if globs is None:
        globs = {}
    else:
        globs = globs.copy()
    if extraglobs is not None:
        globs.update(extraglobs)
    if '__name__' not in globs:
        globs['__name__'] = '__main__'

    if raise_on_error:
        runner = pdoctest.DebugRunner(verbose=verbose, optionflags=optionflags)
    else:
        runner = SymPyDocTestRunner(verbose=verbose, optionflags=optionflags)

    if encoding is not None:
        text = text.decode(encoding)

    # Read the file, convert it to a test, and run it.
    test = parser.get_doctest(text, globs, name, filename, 0)
    runner.run(test)

    if report:
        runner.summarize()

    if pdoctest.master is None:
        pdoctest.master = runner
    else:
        pdoctest.master.merge(runner)

    return SymPyTestResults(runner.failures, runner.tries)

class SymPyTests(object):

    def __init__(self, reporter, kw="", post_mortem=False,
                 seed=random.random()):
        self._post_mortem = post_mortem
        self._kw = kw
        self._count = 0
        self._root_dir = sympy_dir
        self._reporter = reporter
        self._reporter.root_dir(self._root_dir)
        self._testfiles = []
        self._seed = seed

    def test(self, sort=False):
        """
        Runs the tests returning True if all tests pass, otherwise False.

        If sort=False run tests in random order.
        """
        if sort:
            self._testfiles.sort()
        else:
            from random import shuffle
            random.seed(self._seed)
            shuffle(self._testfiles)
        self._reporter.start(self._seed)
        for f in self._testfiles:
            try:
                self.test_file(f)
            except KeyboardInterrupt:
                print(" interrupted by user")
                break
        return self._reporter.finish()

    def test_file(self, filename):
        name = "test%d" % self._count
        name = os.path.splitext(os.path.basename(filename))[0]
        self._count += 1
        gl = {'__file__':filename}
        random.seed(self._seed)
        try:
            exec(compile(open(filename).read(), filename, 'exec'), gl)
        except (ImportError, SyntaxError):
            self._reporter.import_error(filename, sys.exc_info())
            return
        pytestfile = ""
        if "XFAIL" in gl:
            pytestfile = inspect.getsourcefile(gl["XFAIL"])
        disabled = gl.get("disabled", False)
        if disabled:
            funcs = []
        else:
            # we need to filter only those functions that begin with 'test_'
            # that are defined in the testing file or in the file where
            # is defined the XFAIL decorator
            funcs = [gl[f] for f in list(gl.keys()) if f.startswith("test_") and
                                                 (inspect.isfunction(gl[f])
                                                    or inspect.ismethod(gl[f])) and
                                                 (inspect.getsourcefile(gl[f]) == filename or
                                                   inspect.getsourcefile(gl[f]) == pytestfile)]
            # Sorting of XFAILed functions isn't fixed yet :-(
            funcs.sort(key=lambda x: inspect.getsourcelines(x)[1])
            i = 0
            while i < len(funcs):
                if isgeneratorfunction(funcs[i]):
                # some tests can be generators, that return the actual
                # test functions. We unpack it below:
                    f = funcs.pop(i)
                    for fg in f():
                        func = fg[0]
                        args = fg[1:]
                        fgw = lambda: func(*args)
                        funcs.insert(i, fgw)
                        i += 1
                else:
                    i += 1
            # drop functions that are not selected with the keyword expression:
            funcs = [x for x in funcs if self.matches(x)]

        if not funcs:
            return
        self._reporter.entering_filename(filename, len(funcs))
        for f in funcs:
            self._reporter.entering_test(f)
            try:
                f()
            except KeyboardInterrupt:
                raise
            except:
                t, v, tr = sys.exc_info()
                if t is AssertionError:
                    self._reporter.test_fail((t, v, tr))
                    if self._post_mortem:
                        pdb.post_mortem(tr)
                elif t.__name__ == "Skipped":
                    self._reporter.test_skip(v)
                elif t.__name__ == "XFail":
                    self._reporter.test_xfail()
                elif t.__name__ == "XPass":
                    self._reporter.test_xpass(v)
                else:
                    self._reporter.test_exception((t, v, tr))
                    if self._post_mortem:
                        pdb.post_mortem(tr)
            else:
                self._reporter.test_pass()
        self._reporter.leaving_filename()

    def matches(self, x):
        """
        Does the keyword expression self._kw match "x"? Returns True/False.

        Always returns True if self._kw is "".
        """
        if self._kw == "":
            return True
        return x.__name__.find(self._kw) != -1

    def get_test_files(self, dir, pat = 'test_*.py'):
        """
        Returns the list of test_*.py (default) files at or below directory
        `dir` relative to the sympy home directory.
        """
        dir = os.path.join(self._root_dir, convert_to_native_paths([dir])[0])

        g = []
        for path, folders, files in os.walk(dir):
            g.extend([os.path.join(path, f) for f in files if fnmatch(f, pat)])

        return [sys_normcase(gi) for gi in g]

class SymPyDocTests(object):

    def __init__(self, reporter, normal):
        self._count = 0
        self._root_dir = sympy_dir
        self._reporter = reporter
        self._reporter.root_dir(self._root_dir)
        self._normal = normal

        self._testfiles = []

    def test(self):
        """
        Runs the tests and returns True if all tests pass, otherwise False.
        """
        self._reporter.start()
        for f in self._testfiles:
            try:
                self.test_file(f)
            except KeyboardInterrupt:
                print(" interrupted by user")
                break
        return self._reporter.finish()

    def test_file(self, filename):

        import unittest
        from io import StringIO

        rel_name = filename[len(self._root_dir)+1:]
        module = rel_name.replace(os.sep, '.')[:-3]
        setup_pprint()
        try:
            module = pdoctest._normalize_module(module)
            tests = SymPyDocTestFinder().find(module)
        except:
            self._reporter.import_error(filename, sys.exc_info())
            return

        tests = [test for test in tests if len(test.examples) > 0]
        # By default (except for python 2.4 in which it was broken) tests
        # are sorted by alphabetical order by function name. We sort by line number
        # so one can edit the file sequentially from bottom to top...HOWEVER
        # if there are decorated functions, their line numbers will be too large
        # and for now one must just search for these by text and function name.
        tests.sort(key=lambda x: -x.lineno)

        if not tests:
            return
        self._reporter.entering_filename(filename, len(tests))
        for test in tests:
            assert len(test.examples) != 0
            runner = SymPyDocTestRunner(optionflags=pdoctest.ELLIPSIS | \
                    pdoctest.NORMALIZE_WHITESPACE)
            old = sys.stdout
            new = StringIO()
            sys.stdout = new
            # If the testing is normal, the doctests get importing magic to
            # provide the global namespace. If not normal (the default) then
            # then must run on their own; all imports must be explicit within
            # a function's docstring. Once imported that import will be
            # available to the rest of the tests in a given function's
            # docstring (unless clear_globs=True below).
            if not self._normal:
                test.globs = {}
                # if this is uncommented then all the test would get is what
                # comes by default with a "from sympy import *"
                #exec('from sympy import *') in test.globs
            try:
                f, t = runner.run(test, out=new.write, clear_globs=False)
            finally:
                sys.stdout = old
            if f > 0:
                self._reporter.doctest_fail(test.name, new.getvalue())
            else:
                self._reporter.test_pass()
        self._reporter.leaving_filename()

    def get_test_files(self, dir, pat='*.py', init_only=True):
        """
        Returns the list of *py files (default) from which docstrings
        will be tested which are at or below directory `dir`. By default,
        only those that have an __init__.py in their parent directory
        and do not start with `test_` will be included.
        """
        def importable(x):
            """
            Checks if given pathname x is an importable module by checking for
            __init__.py file.

            Returns True/False.

            Currently we only test if the __init__.py file exists in the
            directory with the file "x" (in theory we should also test all the
            parent dirs).
            """
            init_py = os.path.join(os.path.dirname(x), "__init__.py")
            return os.path.exists(init_py)

        dir = os.path.join(self._root_dir, convert_to_native_paths([dir])[0])

        g = []
        for path, folders, files in os.walk(dir):
            g.extend([os.path.join(path, f) for f in files
                      if not f.startswith('test_') and fnmatch(f, pat)])
        if init_only:
            # skip files that are not importable (i.e. missing __init__.py)
            g = [x for x in g if importable(x)]

        return [sys_normcase(gi) for gi in g]

class SymPyDocTestFinder(DocTestFinder):
    """
    A class used to extract the DocTests that are relevant to a given
    object, from its docstring and the docstrings of its contained
    objects.  Doctests can currently be extracted from the following
    object types: modules, functions, classes, methods, staticmethods,
    classmethods, and properties.

    Modified from doctest's version by looking harder for code in the
    case that it looks like the the code comes from a different module.
    In the case of decorated functions (e.g. @vectorize) they appear
    to come from a different module (e.g. multidemensional) even though
    their code is not there.
    """

    def _find(self, tests, obj, name, module, source_lines, globs, seen):
        """
        Find tests for the given object and any contained objects, and
        add them to `tests`.
        """
        if self._verbose:
            print('Finding tests in %s' % name)

        # If we've already processed this object, then ignore it.
        if id(obj) in seen:
            return
        seen[id(obj)] = 1

        # Make sure we don't run doctests for classes outside of sympy, such
        # as in numpy or scipy.
        if inspect.isclass(obj):
            if obj.__module__.split('.')[0] != 'sympy':
                return

        # Find a test for this object, and add it to the list of tests.
        test = self._get_test(obj, name, module, globs, source_lines)
        if test is not None:
            tests.append(test)

        # Look for tests in a module's contained objects.
        if inspect.ismodule(obj) and self._recurse:
            for rawname, val in list(obj.__dict__.items()):
                # Recurse to functions & classes.
                if inspect.isfunction(val) or inspect.isclass(val):
                    in_module = self._from_module(module, val)
                    if not in_module:
                        # double check in case this function is decorated
                        # and just appears to come from a different module.
                        pat = r'\s*(def|class)\s+%s\s*\(' % rawname
                        PAT = pre.compile(pat)
                        in_module = any(PAT.match(line) for line in source_lines)
                    if in_module:
                        try:
                            valname = '%s.%s' % (name, rawname)
                            self._find(tests, val, valname, module, source_lines, globs, seen)
                        except ValueError as msg:
                            raise
                        except:
                            pass

        # Look for tests in a module's __test__ dictionary.
        if inspect.ismodule(obj) and self._recurse:
            for valname, val in list(getattr(obj, '__test__', {}).items()):
                if not isinstance(valname, str):
                    raise ValueError("SymPyDocTestFinder.find: __test__ keys "
                                     "must be strings: %r" %
                                     (type(valname),))
                if not (inspect.isfunction(val) or inspect.isclass(val) or
                        inspect.ismethod(val) or inspect.ismodule(val) or
                        isinstance(val, str)):
                    raise ValueError("SymPyDocTestFinder.find: __test__ values "
                                     "must be strings, functions, methods, "
                                     "classes, or modules: %r" %
                                     (type(val),))
                valname = '%s.__test__.%s' % (name, valname)
                self._find(tests, val, valname, module, source_lines,
                           globs, seen)

        # Look for tests in a class's contained objects.
        if inspect.isclass(obj) and self._recurse:
            for valname, val in list(obj.__dict__.items()):
                # Special handling for staticmethod/classmethod.
                if isinstance(val, staticmethod):
                    val = getattr(obj, valname)
                if isinstance(val, classmethod):
                    val = getattr(obj, valname).__func__

                # Recurse to methods, properties, and nested classes.
                if (inspect.isfunction(val) or
                     inspect.isclass(val) or
                     isinstance(val, property)):
                    in_module = self._from_module(module, val)
                    if not in_module:
                        # "double check" again
                        pat = r'\s*(def|class)\s+%s\s*\(' % valname
                        PAT = pre.compile(pat)
                        in_module = any(PAT.match(line) for line in source_lines)
                    if in_module:
                        valname = '%s.%s' % (name, valname)
                        self._find(tests, val, valname, module, source_lines,
                                   globs, seen)

    def _get_test(self, obj, name, module, globs, source_lines):
        """
        Return a DocTest for the given object, if it defines a docstring;
        otherwise, return None.
        """
        # Extract the object's docstring.  If it doesn't have one,
        # then return None (no test for this object).
        if isinstance(obj, str):
            docstring = obj
        else:
            try:
                if obj.__doc__ is None:
                    docstring = ''
                else:
                    docstring = obj.__doc__
                    if not isinstance(docstring, str):
                        docstring = str(docstring)
            except (TypeError, AttributeError):
                docstring = ''

        # Find the docstring's location in the file.
        lineno = self._find_lineno(obj, source_lines)

        if lineno is None:
            # if None, then _find_lineno couldn't find the docstring.
            # But IT IS STILL THERE.  Likely it was decorated or something
            # (i.e., @property docstrings have lineno == None)
            # TODO: Write our own _find_lineno that is smarter in this regard
            # Until then, just give it a dummy lineno.  This is just used for
            # sorting the tests, so the only bad effect is that they will appear
            # last instead of the order that they really are in the file.
            # lineno is also used to report the offending line of a failing
            # doctest, which is another reason to fix this.  See issue 1947.
            lineno = 0

        # Don't bother if the docstring is empty.
        if self._exclude_empty and not docstring:
            return None

        # Return a DocTest for this object.
        if module is None:
            filename = None
        else:
            filename = getattr(module, '__file__', module.__name__)
            if filename[-4:] in (".pyc", ".pyo"):
                filename = filename[:-1]
        return self._parser.get_doctest(docstring, globs, name,
                                        filename, lineno)

class SymPyDocTestRunner(DocTestRunner):
    """
    A class used to run DocTest test cases, and accumulate statistics.
    The `run` method is used to process a single DocTest case.  It
    returns a tuple `(f, t)`, where `t` is the number of test cases
    tried, and `f` is the number of test cases that failed.

    Modified from the doctest version to not reset the sys.displayhook (see
    issue 2041).

    See the docstring of the original DocTestRunner for more information.
    """

    def run(self, test, compileflags=None, out=None, clear_globs=True):
        """
        Run the examples in `test`, and display the results using the
        writer function `out`.

        The examples are run in the namespace `test.globs`.  If
        `clear_globs` is true (the default), then this namespace will
        be cleared after the test runs, to help with garbage
        collection.  If you would like to examine the namespace after
        the test completes, then use `clear_globs=False`.

        `compileflags` gives the set of flags that should be used by
        the Python compiler when running the examples.  If not
        specified, then it will default to the set of future-import
        flags that apply to `globs`.

        The output of each example is checked using
        `SymPyDocTestRunner.check_output`, and the results are formatted by
        the `SymPyDocTestRunner.report_*` methods.
        """
        self.test = test

        if compileflags is None:
            compileflags = pdoctest._extract_future_flags(test.globs)

        save_stdout = sys.stdout
        if out is None:
            out = save_stdout.write
        sys.stdout = self._fakeout

        # Patch pdb.set_trace to restore sys.stdout during interactive
        # debugging (so it's not still redirected to self._fakeout).
        # Note that the interactive output will go to *our*
        # save_stdout, even if that's not the real sys.stdout; this
        # allows us to write test cases for the set_trace behavior.
        save_set_trace = pdb.set_trace
        self.debugger = pdoctest._OutputRedirectingPdb(save_stdout)
        self.debugger.reset()
        pdb.set_trace = self.debugger.set_trace

        # Patch linecache.getlines, so we can see the example's source
        # when we're inside the debugger.
        self.save_linecache_getlines = pdoctest.linecache.getlines
        linecache.getlines = self.__patched_linecache_getlines

        try:
            return self.__run(test, compileflags, out)
        finally:
            sys.stdout = save_stdout
            pdb.set_trace = save_set_trace
            linecache.getlines = self.save_linecache_getlines
            if clear_globs:
                test.globs.clear()

# We have to override the name mangled methods.
SymPyDocTestRunner._SymPyDocTestRunner__patched_linecache_getlines = \
    DocTestRunner._DocTestRunner__patched_linecache_getlines
SymPyDocTestRunner._SymPyDocTestRunner__run = DocTestRunner._DocTestRunner__run
SymPyDocTestRunner._SymPyDocTestRunner__record_outcome = \
    DocTestRunner._DocTestRunner__record_outcome

class Reporter(object):
    """
    Parent class for all reporters.
    """
    pass

class PyTestReporter(Reporter):
    """
    Py.test like reporter. Should produce output identical to py.test.
    """

    def __init__(self, verbose=False, tb="short", colors=True):
        self._verbose = verbose
        self._tb_style = tb
        self._colors = colors
        self._xfailed = 0
        self._xpassed = []
        self._failed = []
        self._failed_doctest = []
        self._passed = 0
        self._skipped = 0
        self._exceptions = []

        # this tracks the x-position of the cursor (useful for positioning
        # things on the screen), without the need for any readline library:
        self._write_pos = 0
        self._line_wrap = False

    def root_dir(self, dir):
        self._root_dir = dir

    def write(self, text, color="", align="left", width=80):
        """
        Prints a text on the screen.

        It uses sys.stdout.write(), so no readline library is necessary.

        color ... choose from the colors below, "" means default color
        align ... left/right, left is a normal print, right is aligned on the
                  right hand side of the screen, filled with " " if necessary
        width ... the screen width
        """
        color_templates = (
            ("Black"       , "0;30"),
            ("Red"         , "0;31"),
            ("Green"       , "0;32"),
            ("Brown"       , "0;33"),
            ("Blue"        , "0;34"),
            ("Purple"      , "0;35"),
            ("Cyan"        , "0;36"),
            ("LightGray"   , "0;37"),
            ("DarkGray"    , "1;30"),
            ("LightRed"    , "1;31"),
            ("LightGreen"  , "1;32"),
            ("Yellow"      , "1;33"),
            ("LightBlue"   , "1;34"),
            ("LightPurple" , "1;35"),
            ("LightCyan"   , "1;36"),
            ("White"       , "1;37"),  )

        colors = {}

        for name, value in color_templates:
            colors[name] = value
        c_normal = '\033[0m'
        c_color = '\033[%sm'

        if align == "right":
            if self._write_pos+len(text) > width:
                # we don't fit on the current line, create a new line
                self.write("\n")
            self.write(" "*(width-self._write_pos-len(text)))

        if hasattr(sys.stdout, 'isatty') and not sys.stdout.isatty():
            # the stdout is not a terminal, this for example happens if the
            # output is piped to less, e.g. "bin/test | less". In this case,
            # the terminal control sequences would be printed verbatim, so
            # don't use any colors.
            color = ""
        if sys.platform == "win32":
            # Windows consoles don't support ANSI escape sequences
            color = ""

        if self._line_wrap:
            if text[0] != "\n":
                sys.stdout.write("\n")

        if color == "":
            sys.stdout.write(text)
        else:
            sys.stdout.write("%s%s%s" % (c_color % colors[color], text, c_normal))
        sys.stdout.flush()
        l = text.rfind("\n")
        if l == -1:
            self._write_pos += len(text)
        else:
            self._write_pos = len(text)-l-1
        self._line_wrap = self._write_pos >= width
        self._write_pos %= width

    def write_center(self, text, delim="="):
        width = 80
        if text != "":
            text = " %s " % text
        idx = (width-len(text)) // 2
        t = delim*idx + text + delim*(width-idx-len(text))
        self.write(t+"\n")

    def write_exception(self, e, val, tb):
        t = traceback.extract_tb(tb)
        # remove the first item, as that is always runtests.py
        t = t[1:]
        t = traceback.format_list(t)
        self.write("".join(t))
        t = traceback.format_exception_only(e, val)
        self.write("".join(t))

    def start(self, seed=None):
        self.write_center("test process starts")
        executable = sys.executable
        v = tuple(sys.version_info)
        python_version = "%s.%s.%s-%s-%s" % v
        self.write("executable:   %s  (%s)\n" % (executable, python_version))
        from .misc import ARCH
        self.write("architecture: %s\n" % ARCH)
        from sympy.polys.domains import GROUND_TYPES
        self.write("ground types: %s\n" % GROUND_TYPES)
        if seed is not None:
            self.write("random seed: %d\n\n" % seed)
        self._t_start = clock()

    def finish(self):
        self._t_end = clock()
        self.write("\n")
        global text, linelen
        text = "tests finished: %d passed, " % self._passed
        linelen = len(text)
        def add_text(mytext):
            global text, linelen
            """Break new text if too long."""
            if linelen + len(mytext) > 80:
                text += '\n'
                linelen = 0
            text += mytext
            linelen += len(mytext)

        if len(self._failed) > 0:
            add_text("%d failed, " % len(self._failed))
        if len(self._failed_doctest) > 0:
            add_text("%d failed, " % len(self._failed_doctest))
        if self._skipped > 0:
            add_text("%d skipped, " % self._skipped)
        if self._xfailed > 0:
            add_text("%d expected to fail, " % self._xfailed)
        if len(self._xpassed) > 0:
            add_text("%d expected to fail but passed, " % len(self._xpassed))
        if len(self._exceptions) > 0:
            add_text("%d exceptions, " % len(self._exceptions))
        add_text("in %.2f seconds" % (self._t_end - self._t_start))


        if len(self._xpassed) > 0:
            self.write_center("xpassed tests", "_")
            for e in self._xpassed:
                self.write("%s:%s\n" % (e[0], e[1]))
            self.write("\n")

        if self._tb_style != "no" and len(self._exceptions) > 0:
            #self.write_center("These tests raised an exception", "_")
            for e in self._exceptions:
                filename, f, (t, val, tb) = e
                self.write_center("", "_")
                if f is None:
                    s = "%s" % filename
                else:
                    s = "%s:%s" % (filename, f.__name__)
                self.write_center(s, "_")
                self.write_exception(t, val, tb)
            self.write("\n")

        if self._tb_style != "no" and len(self._failed) > 0:
            #self.write_center("Failed", "_")
            for e in self._failed:
                filename, f, (t, val, tb) = e
                self.write_center("", "_")
                self.write_center("%s:%s" % (filename, f.__name__), "_")
                self.write_exception(t, val, tb)
            self.write("\n")

        if self._tb_style != "no" and len(self._failed_doctest) > 0:
            #self.write_center("Failed", "_")
            for e in self._failed_doctest:
                filename, msg = e
                self.write_center("", "_")
                self.write_center("%s" % filename, "_")
                self.write(msg)
            self.write("\n")

        self.write_center(text)
        ok = len(self._failed) == 0 and len(self._exceptions) == 0 and \
                len(self._failed_doctest) == 0
        if not ok:
            self.write("DO *NOT* COMMIT!\n")
        return ok

    def entering_filename(self, filename, n):
        rel_name = filename[len(self._root_dir)+1:]
        self._active_file = rel_name
        self._active_file_error = False
        self.write(rel_name)
        self.write("[%d] " % n)

    def leaving_filename(self):
        if self._colors:
            self.write(" ")
            if self._active_file_error:
                self.write("[FAIL]", "Red", align="right")
            else:
                self.write("[OK]", "Green", align="right")
        self.write("\n")
        if self._verbose:
            self.write("\n")

    def entering_test(self, f):
        self._active_f = f
        if self._verbose:
            self.write("\n"+f.__name__+" ")

    def test_xfail(self):
        self._xfailed += 1
        self.write("f", "Green")

    def test_xpass(self, fname):
        self._xpassed.append((self._active_file, fname))
        self.write("X", "Green")

    def test_fail(self, exc_info):
        self._failed.append((self._active_file, self._active_f, exc_info))
        self.write("F", "Red")
        self._active_file_error = True

    def doctest_fail(self, name, error_msg):
        # the first line contains "******", remove it:
        error_msg = "\n".join(error_msg.split("\n")[1:])
        self._failed_doctest.append((name, error_msg))
        self.write("F", "Red")
        self._active_file_error = True

    def test_pass(self):
        self._passed += 1
        if self._verbose:
            self.write("ok", "Green")
        else:
            self.write(".", "Green")

    def test_skip(self, v):
        self._skipped += 1
        self.write("s", "Green")
        if self._verbose:
            self.write(" - ", "Green")
            self.write(v.message, "Green")

    def test_exception(self, exc_info):
        self._exceptions.append((self._active_file, self._active_f, exc_info))
        self.write("E", "Red")
        self._active_file_error = True

    def import_error(self, filename, exc_info):
        self._exceptions.append((filename, None, exc_info))
        rel_name = filename[len(self._root_dir)+1:]
        self.write(rel_name)
        self.write("[?]   Failed to import", "Red")
        if self._colors:
            self.write(" ")
            self.write("[FAIL]", "Red", align="right")
        self.write("\n")

sympy_dir = get_sympy_dir()
