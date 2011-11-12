#! /usr/bin/python
from bzrlib.bzrdir import BzrDir
from bzrlib import errors
from bzrlib import reconfigure
import os

run_path = '/home/jf/msf/Running'
for path in os.listdir(run_path):
    path = os.path.join(run_path, path, 'unifield-wm')
    if os.path.islink(path):
        continue
    if not os.path.isdir(path):
        continue

    try:
        bzdir = BzrDir.open(path)
        reconfigure.Reconfigure.to_branch(bzdir)
        reconfigure.Reconfigure.to_tree(bzdir)
        rec = reconfigure.Reconfigure.to_checkout(bzdir)
    except (errors.AlreadyCheckout, errors.AlreadyTree, errors.AlreadyBranch, errors.NotBranchError):
        continue
    print "Convert %s"%(path,)
    rec.apply(False)

