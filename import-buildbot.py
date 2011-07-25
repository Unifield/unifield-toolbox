import launchpadlib.launchpad
import re
import xmlrpclib

# ssh -L 6070:localhost:6069 uf0001
dbuser = 'admin'
dbpass = 'admin'
db = 'unibuildbot'
#port = 6069
port = 6070
host = 'localhost'
sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/common'%(host, port))
uid = sock.login(db, dbuser, dbpass)
sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object'%(host, port))

project_id = sock.execute(db, uid, dbpass, 'buildbot.lp.project', 'search', [('name','like','addons')])
if not project_id:
    raise Exception('No project')

max_port_ids = sock.execute(db, uid, dbpass, 'buildbot.lp.branch', 'search', [('port','!=',0)], 0, 1, 'port')
maxport = 6080
if max_port_ids:
	maxport = sock.execute(db, uid, dbpass, 'buildbot.lp.branch', 'read', max_port_ids, ['port'])[0]['port']

project_id = project_id[0]

branch_ids = sock.execute(db, uid, dbpass, 'buildbot.lp.branch','search',[('is_test_branch','=',False), ('is_root_branch','=',False), ('active', 'in', ['t','f'])])
openerp_branch = {}
if branch_ids:
    for op in sock.execute(db, uid, dbpass, 'buildbot.lp.branch', 'read', branch_ids, ['name','url']):
    	openerp_branch[op['url']] = op['id']


launchpad=launchpadlib.launchpad.Launchpad.login_with('jfb-tempo-consulting', 'production')
#team=launchpad.people['unifield-team']
#team_branches=team.getBranches()
project = launchpad.projects['unifield-wm/trunk']
url = 'bzr+ssh://bazaar.launchpad.net/'
active = []
#for b in [br for br in team_branches if re.search('/unifield-wm/',br.unique_name)]:
for mp in project.branch.getMergeProposals():
    b = mp.source_branch
    brurl = '%s%s'%(url, b.unique_name)
    if brurl not in openerp_branch:
    	vals = {
	    'url': brurl,
	    'lp_project_id': project_id, 
	    'latest_rev_no': b.revision_count - 1,
	    'merge_extra_addons': True,
	    'addons_include': 'msf_profile',
	    'active': True,
	    'name': b.name,
	    'treestabletimer': 30,
	    'port': maxport+2,
	    'netport': maxport+3,
        }
        maxport += 2
        new_id = sock.execute(db, uid, dbpass, 'buildbot.lp.branch','create', vals)
        active.append('%s: %s'%(b.name, new_id))
    else:
        del(openerp_branch[brurl])

#if openerp_branch:
    #sock.execute(db, uid, dbpass, 'buildbot.lp.branch', 'write', openerp_branch.values(), {'active': False})
#    print "Desactivation: %s"%(openerp_branch.keys())

if active:
    print "Activation: %s"%(", ".join(active))
