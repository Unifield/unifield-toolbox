#-*- coding:utf-8 -*-
import oerplib
import argparse
import re
import subprocess


DEFAULT_XMLRPC_PORT = 8069
DEFAULT_SERVER = "localhost"
RUNBOT_URL = "rb.unifield.org"


parser = argparse.ArgumentParser()
parser.add_argument("-s", "--server", default=DEFAULT_SERVER, help="Server URL (default: %s)" % DEFAULT_SERVER)
parser.add_argument("-p", "--port", type=int, default=DEFAULT_XMLRPC_PORT, help="XMLRPC port to use (default: %s)" % DEFAULT_XMLRPC_PORT)
parser.add_argument("-u", "--user", default="admin", help="Unifield user to connect to the database (default: admin)")
parser.add_argument("-w", "--password", default="admin", help="Unifield password to connect to the database (default: admin)")
parser.add_argument("-d", "--database", help="Target database")
args = parser.parse_args()

args.server = args.server.strip('/ ')

if args.server.startswith('http://'):
	args.server = args.server[7:]

if args.server not in ('localhost', '127.0.0.1'):
	# if only the user name of the RB is given, complete URL:
	if args.server.find('.unifield.org') == -1:
		server_url = args.server + '.' + RUNBOT_URL
		url_choice = raw_input("Server URL = %s, use this value ? (y or n) " % server_url)
		if url_choice.lower() in ('y', 'yes'):
			args.server = server_url

	# try to get the XMLRPC port from runbot:
	port_found = False
	try:
		rb_name = args.server.split('.')[0]
		cmd = "scp -q root@%s:/home/%s/RB_info.txt /tmp/%s_info.txt" % ('.'.join(args.server.split('.')[1:]), rb_name, rb_name)
		subprocess.call(cmd.split(" "))
		fich = open("/tmp/%s_info.txt" % rb_name)
		content = fich.read()
		line = re.search(r'XML-RPC port.*', content).group()
		port_found = int(line.split(' ')[-1])
		fich.close()
	except:
		pass
	if port_found and port_found != args.port:
		port_choice = raw_input("Auto XMLRPC port = %s, use this value ? (y or n) " % port_found)
		if port_choice.lower() in ('y', 'yes'):
			args.port = port_found


print "Connecting to %s on port %s ..." % (args.server, args.port),
oerp = oerplib.OERP(server=args.server, protocol='xmlrpc', port=args.port, timeout=3600, version='6.0')
print "done"

# if target database not given, list all dbs and ask user to choose:
if not args.database:
	if not oerp.db.list():
		print "No database found."
		exit(1)
	print "Target database:"
	i = 1
	for db in oerp.db.list():
		print "\t%s) %s" % (i, db)
		i += 1
	input_ok = False
	while not input_ok:
		db_choice = raw_input("Your choice ? ")
		try: 
			db_choice = int(db_choice)
		except:
			continue
		if db_choice > 0 and db_choice <= len(oerp.db.list()):
			input_ok = True
	args.database = oerp.db.list()[db_choice-1]

print "Logging as %s on %s ..." % (args.user, args.database),
user = oerp.login(args.user, args.password, args.database)
print "done"
