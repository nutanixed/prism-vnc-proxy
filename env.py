#
# Copyright (c) 2012 Nutanix Inc. All rights reserved.
#
# Author: cui@nutanix.com
#
# This module sets up Python path for the rest of infrastructure code.
#

# Assertions: tool for (1) documenting, (2) debugging, and (3) testing code during development
# In Python, assertions are statements that you can use to set sanity checks during the development process
# The assertion condition should always be true unless you have a bug in your program

# With assertions, you can set checks to make sure that invariants within your code stay invariant.
# In computer science, an invariant is a logical assertion that is always held to be true during a certain 
  # phase of execution of a computer program.

# By doing so, you can check assumptions like preconditions and postconditions.
# For example, you can test conditions along the lines of This argument is not None or This return value is a string.
# These kinds of checks can help you catch errors as soon as possible when you’re developing a program.

# In general, you shouldn’t use assertions for data processing or data validation, because you can disable assertions 
  # in your production code, which ends up removing all your assertion-based processing and validation code.

# Assertions aren’t an error-handling tool.
# The ultimate purpose of assertions isn’t to handle errors in production
# but to notify you during development so that you can fix them.

# In this regard, you shouldn’t write code that catches assertion errors using a regular try … except statement.

# Python implements assertions as a [statement] with the 'assert' [keyword] rather than as a [function].
# This behavior can be a common source of confusion and issues, as you’ll learn later in this tutorial.

# =====================================================================================================================

# In Python, 'assert' is a simple statement with the following syntax:

    # assert expression[, assertion_message]

# 'expression' above can be [any valid Python expression or object], which is then [tested] for [truthiness].

#  If 'expression' is [false], then the statement throws an [AssertionError].

# The 'assertion_message' parameter is [optional] but [encouraged].

# It can hold a string describing the issue that the statement is supposed to catch.

# =======================================================================================================================

# if __name__ == '__main__'   >>>   allows you to [execute code] when the [file] runs as a [script], but [NOT] when it is [imported] as a [module].

# if __name__ == "__main__" is a way to store code that should only run when your file is executed as a script.

# assertions can be disabled to improve performance in production

assert __name__ != "__main__", "This module should NOT be executed."




import os

# PYTHON 2.x  :  os.listdir()  -  to get a list To get a list of all the files and folders in a particular directory in the filesystem

# PYTHON 3.x  :  os.scandir()  -  the preferred method to use if you also want to get file and directory properties such as file size and modification date.

# In modern versions of Python, an alternative to [os.listdir()] is to use [os.scandir()] and [pathlib.Path()].


import sys

# Add everything in lib/py (relative to env.py) to sys.path.
_PYLIBS_PATH = os.path.abspath(
  os.path.join(os.path.dirname(__file__), "lib/py"))

# If lib/py exists, then we only want to use libraries from there.
if os.path.isdir(_PYLIBS_PATH):
  # Prepend everything in lib/py to sys.path.
  for path in os.listdir(_PYLIBS_PATH):
    sys.path.insert(0, os.path.join(_PYLIBS_PATH, path))

__all__ = []



# with the introduction of [importlib.resources] into the standard library in Python 3.7, there’s now one standard way of dealing with [resource files].


