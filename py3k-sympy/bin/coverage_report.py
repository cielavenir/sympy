#!/usr/bin/env python3
"""
Script to generate test coverage reports.

Usage:

$ bin/coverage_report.py

This will create a directory covhtml with the coverage reports.To restrict the analysis
to a directory, you just need to pass its name as
argument. For example:

$ bin/coverage_report.py sympy/logic

runs only the tests in sympy/logic/ and reports only on the modules in
sympy/logic/.  You can also get a report on the parts of the whole sympy code
covered by the tests in sympy/logic/ by following up the previous command with

$ bin/coverage_report.py -c

"""
import os, sys, re
from optparse import OptionParser

try:
    import coverage
except ImportError:
    print("You need to install module coverage. See http://nedbatchelder.com/code/coverage/")
    sys.exit(-1)

REPORT_DIR = "covhtml"
REFRESH = False

omit_dir_patterns= ['.*tests', 'benchmark', 'examples',
                    'mpmath', 'pyglet', 'test_external']
omit_dir_re = re.compile(r'|'.join(omit_dir_patterns))
source_re = re.compile(r'.*\.py$')

def generate_covered_files(top_dir):
    for dirpath, dirnames, filenames in os.walk(top_dir):
        omit_dirs = [dirn for dirn in dirnames if omit_dir_re.match(dirn)]
        for x in omit_dirs:
            dirnames.remove(x)
        for filename in filenames:
            if source_re.match(filename):
                yield os.path.join(dirpath, filename)


def make_report(source_dir, report_dir, use_cache=False):
    #code adapted from /bin/test
    bin_dir = os.path.abspath(os.path.dirname(__file__))         # bin/
    sympy_top  = os.path.split(bin_dir)[0]      # ../
    sympy_dir  = os.path.join(sympy_top, 'sympy')  # ../sympy/
    if os.path.isdir(sympy_dir):
        sys.path.insert(0, sympy_top)
    os.chdir(sympy_top)

    cov = coverage.coverage()
    cov.exclude("raise NotImplementedError")
    cov.exclude("def canonize")      #this should be "@decorated"
    if use_cache:
        cov.load()
    else:
        cov.erase()
        cov.start()
        import sympy
        sympy.test(source_dir)
        #sympy.doctest()        #coverage doesn't play well with doctests
        cov.stop()
        cov.save()

    covered_files = list(generate_covered_files(source_dir))

    if report_dir in os.listdir(os.curdir):
        for f in os.listdir(report_dir):
            if f.split('.')[-1] in ['html', 'css', 'js']:
                os.remove(os.path.join(report_dir, f))

    cov.html_report(morfs=covered_files, directory=report_dir)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-c', '--use-cache', action='store_true', default=False,
                        help='Use cached data.')
    parser.add_option('-d', '--report-dir', default='covhtml',
                        help='Directory to put the generated report in.')

    options, args = parser.parse_args()

    if args:
        source_dir = args[0]
    else:
        source_dir = 'sympy/'

    make_report(source_dir, **options.__dict__)
