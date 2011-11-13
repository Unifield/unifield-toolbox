#!/usr/bin/python
import sys

import cgitb,os,re,subprocess,time
import argparse
import fileinput
import mako.template
from lib import initdb
import ConfigParser
import psycopg2
import psycopg2.extensions
from bzrlib.branch import Branch
from bzrlib.branch import BzrBranch
from bzrlib.bzrdir import BzrDir
from bzrlib.workingtree import WorkingTree
from bzrlib.plugins.launchpad.lp_directory import LaunchpadDirectory
from bzrlib import missing
import shutil
import smtplib 
from lib import jira_lib
from email.mime.text import MIMEText
import getpass
from datetime import datetime 
#----------------------------------------------------------
# OpenERP rdtools utils
#----------------------------------------------------------

def write_pid(pidfile, pid):
    pidf = open(pidfile, "w")
    pidf.write("%d"%pid)
    pidf.close()

def log(*l,**kw):
    out=[time.strftime("%Y-%m-%d %H:%M:%S")]
    for i in l:
        if not isinstance(i,basestring):
            i=repr(i)
        out.append(i)
    out+=["%s=%r"%(k,v) for k,v in kw.items()]
    sys.stdout.write(" ".join(out))
    sys.stdout.write("\n")

def run(l):
    log("run",*l)
    if isinstance(l,list):
        rc=os.spawnvp(os.P_WAIT, l[0], l)
    elif isinstance(l,str):
        tmp=['sh','-c',l]
        rc=os.spawnvp(os.P_WAIT, tmp[0], tmp)
    return rc

def kill(pid,sig=9):
    try:
        os.kill(pid,sig)
    except OSError:
        pass
    
def _is_running(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return pid
    except OSError:
        return False

def underscorize(n):
    return n.replace("~","").replace(":","_").replace("/","_")

#----------------------------------------------------------
# OpenERP RunBot
#----------------------------------------------------------

class RunBotBranch(object):
    def __init__(self,runbot, subfolder):
        self.runbot=runbot
        self.running=False
        self.running_port=None
        self.running_server_pid=None
        self.running_web_pid=None
        self.running_t0=None
        self.date_last_modified=0
        self.revision_count=0
        self.merge_count=0
        self.revno = {}

        self.name = subfolder
        self.unique_name = subfolder
        self.project_name = subfolder
        self.uname=underscorize(self.unique_name)

        self.subdomain=subfolder
        self.instance_path=os.path.join(self.runbot.wd, "running", self.subdomain)
        self.email_alias = {
            'pam': 'patrick.amstutz@geneva.msf.org',
            'pa': 'patrick.amstutz@geneva.msf.org',
            'jfb': 'jfb@tempo-consulting.fr',
            'mc': 'Matthias.CHARDON@geneva.msf.org',
            'md': 'Matthieu.DIETRICH@geneva.msf.org',
            'od': 'od@tempo-consulting.fr',
            'ml': 'Magali.LAPIERE@geneva.msf.org',
            'mm': 'mm@tempo-consulting.fr',
            'sr': 'Sebastien.ROCHE@geneva.msf.org',
            'qt': 'qt@tempo-consulting.fr',
            'dv': 'Duy.VO@geneva.msf.org',
        }
        self.server_path=os.path.join(self.instance_path,"unifield-server")
        self.server_bin_path=os.path.join(self.server_path,"openerp-server.py")
        if not os.path.exists(self.server_bin_path): # for 6.0 branches
            self.server_bin_path=os.path.join(self.server_path,"bin","openerp-server.py")

        self.data_path = os.path.join(self.instance_path,"unifield-data")

        self.web_path=os.path.join(self.instance_path,"unifield-web")
        self.etc_path = os.path.join(self.instance_path,"etc")
        self.web_bin_path=os.path.join(self.web_path,"openerp-web.py")

        self.log_path=os.path.join(self.instance_path, 'logs')
        self.log_server_path=os.path.join(self.log_path,'server.txt')
        self.log_web_path=os.path.join(self.log_path,'web.txt')
        self.file_pidweb = os.path.join(self.instance_path,'etc','web.pid')
        self.file_pidserver = os.path.join(self.instance_path,'etc','server.pid')
        self.configfile = os.path.join(self.instance_path,'config.ini')
        
        self.ini = ConfigParser.ConfigParser()
        self.ini.readfp(open(self.runbot.common_configfile, 'r'))
        self.ini.read(self.configfile)
        if not self.ini.has_section('global'):
            self.ini.add_section('global')

    def get_uf_from_log(self):
        remote = Branch.open(os.path.join(self.runbot.common_path, 'unifield-wm'))
        wm_path = os.path.join(self.instance_path, 'unifield-wm')
        if os.path.islink(wm_path) or not os.path.isdir(wm_path):
            return 
        wk = Branch.open(wm_path)
        all_uf = {}
        for miss in missing.find_unmerged(wk, remote, restrict='local', include_merges=True)[0]:
            for m in re.finditer("([0-9]{3,})", wk.repository.get_revision(miss[1]).message.encode('utf-8')):
                all_uf[m.group(1)] = True
        detected_uf = sorted(all_uf.keys())
        conf_uf = []
        log("Set detected-uf %s: %s"%(self.instance_path, ','.join(detected_uf)))
        self.set_ini('detected-uf', ','.join(detected_uf))
        self.write_ini()

    def get_revno(self, module):
        return self.runbot.get_revno_from_path(os.path.join(self.instance_path,module))

    def write_ini(self):
        f = open(self.configfile, "w")
        self.ini.write(f)
        f.close()

    def remove_option(self, key):
        try:
            return self.ini.remove_option('global', key)
        except ConfigParser.NoOptionError:
            return False

    def get_ini(self, key):
        try:
            return self.ini.get('global', key)
        except ConfigParser.NoOptionError:
            return False
    
    def get_int_ini(self, key):
        try:
            return self.ini.getint('global', key)
        except ConfigParser.NoOptionError:
            return False

    def get_bool_ini(self, key, default=False):
        try:
            return self.ini.getboolean('global', key)
        except ConfigParser.NoOptionError:
            return default

    def set_ini(self, key, value):
        return self.ini.set('global', key, '%s'%value)

    def is_web_running(self):
        pid = self.pidweb()
        return _is_running(pid)

    def is_server_running(self):
        pid = self.pidserver()
        return _is_running(pid)

    def _get_pid(self, pidfile):
        if not os.path.isfile(pidfile):
            return False
        try:
            pf = file(pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
            return pid
        except IOError:
            return False
        return False

    def pidweb(self):
        return self._get_pid(self.file_pidweb)

    def pidserver(self):
        return self._get_pid(self.file_pidserver)

    def start_createdb(self):
        dbname = self.subdomain.lower()
        try:
            conn = psycopg2.connect(database=dbname)
            log("Database %s exists"%(dbname, ))
        except psycopg2.OperationalError:
            log("Creating database %s"%(dbname, ))
            self.set_ini('db_created', time.strftime("%Y-%m-%d %H:%M:%S"))
            conn = psycopg2.connect(database='template1')
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            c = conn.cursor()
            c.execute('CREATE DATABASE %s'%(dbname, ))
        conn.close()

    def start_run_server(self,port):
        if self.is_server_running():
            log("run","Server %s already running ..."%(self.subdomain, ))
            return True
        
        log("branch-start-run-server", self.project_name, port=port)
        out=open(self.log_server_path,"a")
        
        config_file = os.path.join(self.instance_path,'etc', 'openerprc')

        
        dbname = self.subdomain.lower()
        cmd=[self.server_bin_path,"-c",config_file, "-d",dbname,"--no-xmlrpc","--no-xmlrpcs","--netrpc-port=%d"%(port)]

        modules = self.get_ini('modules')
        if not modules:
            modules = 'base'

        if 'msf_profile' not in modules:
            self.set_ini('load_data',0)

        cmd += ['-i', modules]
         
        if self.get_bool_ini('load_data') or not self.get_bool_ini('load_demo'):
                cmd.append("--without-demo=all")

        log("run",*cmd,log=self.log_server_path)
        p=subprocess.Popen(cmd, stdout=out, stderr=out, close_fds=True)
        self.running_server_pid=p.pid
        write_pid(self.file_pidserver, p.pid)
    
        if self.get_bool_ini('load_data') and not self.get_bool_ini('data_already_loaded'):
            pid = os.fork()
            if not pid:
                self._symlink_nginx_icon('nok')
                try:
                    msg = initdb.connect_db('admin', 'admin', dbname, '127.0.0.1', port, self.data_path, self.file_pidserver+'_')
                except Exception, e:
                    self._email(str(e), True)
                    log('init', self.name, str(e))
                    sys.exit(1)
                self._symlink_nginx_icon('ok')
                if self.get_ini('comment'):
                    msg += "\n\n%s"%(self.get_ini('comment'), )
                self._email(msg)
                sys.exit(1)
            self.set_ini('data_already_loaded', '1')
        else:
            self._symlink_nginx_icon('ok')

    def _email(self, msg, err=False):
        dest = self.get_ini('email')
        if self.runbot.smtp_host and dest:
            if err:
                data ="Unable to initialize %s.\n\n%s\n\n"%(self.name, msg)
            else:
                data ="Your instance is ready: http://%s.%s\n%s\n\n"%(self.subdomain, self.runbot.domain, msg)

            new_dest = []
            for d in dest.split(','):
                new_dest.append(self.email_alias.get(d, d))

            data += "http://%s"%(self.runbot.domain, )
            msg = MIMEText(data)

            msg['Subject'] = 'Runbot %s'%(self.name, )
            msg['To'] = ','.join(new_dest)
            msg['From'] = 'noreply@%s'%(self.runbot.domain, )

            s = smtplib.SMTP(self.runbot.smtp_host)
            s.sendmail(msg['From'], new_dest, msg.as_string())



    def _symlink_nginx_icon(self, itype):
        # assert itype in ['ok', 'nok']
        dest = os.path.join(self.runbot.nginx_path, '%s.png'%(self.name,))
        os.path.exists(dest) and os.remove(dest)
        src = os.path.join(self.runbot.nginx_path,'%s.png'%(itype, ))
        os.symlink(src, dest)
        # Touch file to disable cache
        os.utime(src, None)


    def start_run_web(self,port):
        if self.is_web_running():
            log("run","Web %s already running ..."%(self.subdomain, ))
            return True

        config="""[global]
server.environment = "development"
server.socket_host = "0.0.0.0"
server.socket_port = %d
server.thread_pool = 10
tools.sessions.on = True
log.access_level = "INFO"
log.error_level = "INFO"
tools.csrf.on = False
tools.log_tracebacks.on = False
tools.cgitb.on = True
openerp.server.host = 'localhost'
openerp.server.port = %d
openerp.server.protocol = 'socket'
openerp.server.timeout = 1500
tools.proxy.on = True
[openerp-web]
dblist.filter = 'BOTH'
dbbutton.visible = True
company.url = ''
"""%(port+1,port)

        config_file = os.path.join(self.etc_path,"openerp-web.cfg")
        open(config_file,"w").write(config)

        out=open(self.log_web_path,"a")
        cmd=[self.web_bin_path, '-c', config_file]
        
        log("run",*cmd,log=self.log_web_path)
        p=subprocess.Popen(cmd, stdout=out, stderr=out, close_fds=True)
        self.running_web_pid=p.pid
        write_pid(self.file_pidweb, p.pid)

    def start(self):
        port = self.get_int_ini('port')
        log("branch-start",branch=self.unique_name,port=port)
        
        '''
        Here check if the instance existed already, then do not drop and recreate the DB, just launch the server and web!
        '''
      
        self.start_createdb()

        version = True
        if not self.is_web_running() or not self.is_server_running(): 
            for module in ['unifield-web', 'unifield-server', 'unifield-wm', 'unifield-addons']:
                m_path = os.path.join(self.instance_path, module)
                if os.path.islink(m_path):
                    init_rev = self.get_int_ini('%s-revno'%(module, ))
                    new_rev = self.get_revno(module)
                    if init_rev != new_rev:
                        sys.stderr.write("Instance %s, module %s: revno (%s) has changed since the last start (%s).\n\tDelete %s-revno in %s\n\tor replace the link by: bzr checkout lp:%s -r %s\n"%
                            (self.name, module, new_rev, init_rev, module, self.configfile, module, init_rev));
                        version = False

        if version:
            self.start_run_server(port)
            self.start_run_web(port)

            self.runbot.running.insert(0,self)
            self.runbot.running.sort(key=lambda x:x.date_last_modified,reverse=1)
            self.running_t0=time.time()
            self.running=True
            self.running_port=port
        else:
            sys.stderr.write("Instance %s not started\n"%(self.name,))

        self.write_ini()

    def stop(self):
        log("branch-stop",branch=self.unique_name,port=self.running_port)
        pidserver = self.pidserver()
        if pidserver:
            log('Kill server %s'%(pidserver,))
            kill(pidserver)
        pidweb = self.pidweb()
        if pidweb:
            log('Kill server %s'%(pidweb,))
            kill(pidweb)
        if self in self.runbot.running:
            self.runbot.running.remove(self)
        self.running=False
        self.running_port=None

    def delete(self, onlydb):
        self.stop()
        log("Delete db %s"%self.subdomain.lower())
        run(['dropdb', self.subdomain.lower()])
        if not onlydb:
            log("Delete %s"%self.instance_path)
            shutil.rmtree(self.instance_path)
            try:
                os.remove(os.path.join(self.runbot.nginx_path, '%s.png'%(self.name, )))
            except OSError, e:
                pass
        else:
            self.set_ini('data_already_loaded',0)
            self.write_ini()

        del(self.runbot.uf_instances[self.name])
    
    def init_folder(self):

        ''' To do the following things if not exist
            - create the logs folder for storing log files
            - create soft-link to: unifield-server, unifield-addons, unifield-web if not exist (in case no change has been made)
        '''
        
        logs_dir = os.path.join(self.instance_path, "logs")
        if not os.path.exists(logs_dir):
            os.mkdir(logs_dir)

        # copy the unifield-server project from 'common' folder if not existed
        self.create_module("unifield-server")
        self.create_module("unifield-web")
        # copy the folder 'etc' from 'common' folder, then fill the instance path
        self.process_folder_etc()

        # create softlinks for these 3 projects if not existed
        self.create_module("unifield-addons")
        if self.create_module("unifield-wm"):
            self.get_uf_from_log()

        self.create_module("unifield-data")


    def process_folder_etc(self):
        # delete and recopy the folder "etc"
        project_path = self.etc_path
        #run(["rm","-r", project_path]) # delete first
        
        if not os.path.exists(os.path.join(project_path)):
            run(["cp","-r", self.runbot.common_etc, self.instance_path])
        
            # replace the UF_ADDONS_PATH with the modules path of the current instance 
            config_file = os.path.join(project_path, 'openerprc')
            for line in fileinput.FileInput(config_file, inplace=1):
                line = line.replace("UF_ADDONS_PATH", self.instance_path)
                line = line.replace("UF_INSTANCE", self.name)
                line = line.replace("PIDFILE", self.file_pidserver+'_')
                sys.stdout.write(line)

    def create_module(self, module):
        project_path = os.path.join(self.instance_path, module)
        common_project_path = os.path.join(self.runbot.common_path, module)
        source_module = self.get_ini(module)
        first = True
        if not os.path.exists(project_path):
            if not source_module or source_module == 'link':
                log('Link module %s'%(module, ))
                run(["ln","-s", common_project_path, project_path])
            else:
                directory = LaunchpadDirectory()
                d = directory._resolve(source_module)
                log('bzr checkout %s'%(d, ))
                br = Branch.open(d)

                # for symlink
                common_project_path = os.path.realpath(common_project_path)
                orig = WorkingTree.open(common_project_path)
                br.create_checkout(project_path, lightweight=module!='unifield-wm', accelerator_tree=orig)
                br.repository._client._medium.disconnect()
             
            newrevno = self.runbot.get_revno_from_path(project_path)
            self.set_ini('%s-revno'%(module, ), newrevno)
        else:
            if source_module == 'link' and not os.path.islink(project_path):
                wk = WorkingTree.open(project_path)
                if isinstance(wk.branch, BzrBranch):
                    parent = wk.branch.get_parent()
                    if parent is None:
                        parent = wk.branch.get_bound_location()
                else:
                    parent = wk.branch.bzrdir.root_transport.base
                to_remove = 'bzr+ssh://bazaar.launchpad.net/'
                if parent and parent.startswith(to_remove):
                    parent = parent.replace(to_remove,'lp:')
                    if parent[-1] == '/':
                        parent = parent[0:-1]
                    remove_bis = '%2Bbranch/'
                    if parent.startswith('lp:'+remove_bis):
                        parent = parent.replace(remove_bis, '')
                    self.set_ini(module, parent)
            if not self.get_ini('%s-revno'%(module, )):
                newrevno = self.runbot.get_revno_from_path(project_path)
                self.set_ini('%s-revno'%(module, ), newrevno)
            else:
                newrevno = self.get_ini('%s-revno'%(module, ))
                first = False

        self.revno[module] = newrevno
        return first


class RunBot(object):
    def __init__(self, wd, server_port, nginx_port, domain, init, smtp_host):
        self.wd=wd
        self.common_path = os.path.join(self.wd,"common")
        self.common_etc = os.path.join(self.common_path,"etc")
        self.common_configfile = os.path.join(self.common_etc,"default_config.ini")
        self.server_port=int(server_port)
        self.nginx_port=int(nginx_port)
        self.domain=domain
        self.uf_instances={}
        self.now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.running=[]
        self.nginx_path = os.path.join(self.wd,'nginx')
        self.nginx_pid_path = os.path.join(self.nginx_path,'nginx.pid')
        self.smtp_host = smtp_host
        self.jira_url = 'http://jira.unifield.org/browse/UF-'
        self.bzr_url = 'https://code.launchpad.net/'
        self.state_icon = {'Runbot Validated': 'ok.gif', 'Closed': 'close.gif', 'Integrated': 'close.gif', 'Dev Validated': 'close.gif', 'Runbot Available': 'wait.gif', 'Reopened': 'reop.gif', 'In Progress': 'reop.gif'}
        self.icon_jira_dir = 'Jira'

        self.running_path=os.path.join(self.wd, "running")
        allsubdirs = self.subdirs(self.running_path) # in consumption that the sub-folder NAMES are valid

        self.revno = {}
        for br in ['wm', 'data', 'server', 'web', 'addons']:
            self.revno[br] = self.get_revno_from_path(os.path.join(self.common_path, 'unifield-%s'%(br, )), True)

        for folder in allsubdirs:
            rbb=self.uf_instances.setdefault(folder, RunBotBranch(self,folder))
            if init and rbb.get_bool_ini('start',True):
                rbb.init_folder()

    def get_revno_from_path(self, path, full=False):
        log("Get revno %s"%(path,))
        if os.path.islink(path):
            path = os.path.realpath(path)
        wt = WorkingTree.open(path)
        lr = wt.last_revision()
        try:
            revno = wt.branch.revision_id_to_dotted_revno(lr)[0]
        except:
            revno = False

        if not full:
            return revno
        rev = wt.branch.repository.get_revision(lr)
        return {'revno': revno, 'lastmsg': rev.get_summary(), 'time': datetime.fromtimestamp(rev.timestamp).strftime("%d/%m/%y %H:%M")}

    def is_nginx_running(self):
        return _is_running(self.nginx_pid())

    def nginx_pid(self):
        if os.path.isfile(self.nginx_pid_path):
            return int(open(self.nginx_pid_path).read())
        else:
            return False

    def nginx_reload(self):
        pid = self.nginx_pid()
        if pid:
            os.kill(pid,1)
        else:
            run(["/usr/sbin/nginx","-p", self.wd + "/", "-c", os.path.join(self.nginx_path,"nginx.conf")])

    def nginx_config(self):
        template="""
        pid nginx/nginx.pid;
        error_log nginx/error.log;
        worker_processes  1;
        events { worker_connections  1024; }
        http {
          include /etc/nginx/mime.types;
          server_names_hash_bucket_size 128;
          autoindex on;
          client_body_temp_path nginx; proxy_temp_path nginx; fastcgi_temp_path nginx; access_log nginx/access.log; index index.html;
          server { listen ${r.nginx_port} default; server_name _; root ./nginx/; }
          % for i in r.running:
             server {
                listen ${r.nginx_port};
                server_name ${i.subdomain}.${r.domain};
                location /${i.subdomain}/logs/ { alias ${i.log_path}/; }
                location / { proxy_pass http://127.0.0.1:${i.running_port+1}; proxy_set_header X-Forwarded-Host $host; }
             }
          % endfor
        }
        """
        return mako.template.Template(template).render(r=self)

    def nginx_index_time(self,t):
        for m,u in [(86400,'d'),(3600,'h'),(60,'m')]:
            if t>=m:
                return str(int(t/m))+u
        return str(int(t))+"s"

    def nginx_index(self):
        template = """<!DOCTYPE html>
        <html>
        <head>
        <title>UniField Runbot</title>
        <link rel="shortcut icon" href="/favicon.ico" />
        <link rel="stylesheet" href="style.css" type="text/css">
        </head>
        <body id="indexfile">
        <div id="header">
            <div class="content"><h1>UniField Manual Runbot</h1> </div>
        </div>
        <div id="index">
        <table class="index">
        <thead>
        <tr>
            <td colspan='3'><hr/></td>
        </tr>
        <tr class="tablehead">
            <th class="name left" align="left">UniField test instance</th>
            <th>Date</th>
            <th>Logs</th>
        </tr>
        <tr>
            <td colspan='3'><hr/></td>
        </tr>
        <tr>
            <td colspan='3'></td>
        </tr>
        </thead>
        <tfoot>
        <tr>
            <td colspan='3'></td>
        </tr>
        <tr>
            <td colspan='3'></td>
        </tr>
        <tr class="total">
            <td class="name left"><b>${len(r.running)} UniField test instances</b></td>
            <td></td>
            <td></td>
            <td class="right"></td>
        </tr>
        </tfoot>
        <tbody>
        % for i in sorted(r.running, cmp=lambda x,y: cmp(x.subdomain.lower(),y.subdomain.lower())):
        <tr class="file">
            <td class="name left">
                <a href="http://${i.subdomain}.${r.domain}/"  target="_blank">${i.subdomain}</a> <small>(netrpc: ${i.running_port+1})</small> <img src="${i.subdomain}.png" alt=""/>
            </td>
            <td class="date">
                % if i.get_ini('db_created'):
                    ${i.get_ini('db_created')}
                % else:
                    <span style="color:red;">${r.now}</span>
                % endif

            </td>
            <td>
                <a href="http://${i.subdomain}.${r.domain}/${i.subdomain}/logs/server.txt">server</a>
                <a href="http://${i.subdomain}.${r.domain}/${i.subdomain}/logs/web.txt">web</a>
            </td>
        </tr>
             % if i.get_ini('comment'):
                <tr>
                   <td colspan="3" class="comment">${i.get_ini('comment')}</td>
                </tr>
             % endif
             <% 
                jira_id = i.get_ini('jira-id') and i.get_ini('jira-id').split(',') or []
                detected_uf = i.get_ini('detected-uf') and i.get_ini('detected-uf').split(',') or []
             %>
             % if jira_id or detected_uf:
                    <tr>
                        <td colspan="3" class="comment">
                        |
                        % for jid in sorted(set(jira_id+detected_uf)):
                            <% 
                              color = jid in jira_id and jid not in detected_uf and 'black' or jid not in jira_id and jid in detected_uf and 'red' or 'blue'
                            %>
                            <a style="color:${color}" href="${r.jira_url}${jid}">UF-${jid}</a><img src="${r.icon_jira_dir}/${jid}.gif" />  | 
                        % endfor
                        </td>
                    </tr>
             % endif
	<tr>
            <td colspan="3" class="comment">
            % for br in ['wm', 'data', 'server', 'web']:
                % if i.get_ini('unifield-%s'%(br, )) != 'link':
                         ${br}:<a href="${r.bzr_url}${i.get_ini('unifield-%s'%(br, )).split(':')[-1]}">${i.get_ini('unifield-%s'%(br, )).split(':')[-1].split('/')[-1]}</a>@<a href="https://bazaar.launchpad.net/${i.get_ini('unifield-%s'%(br, )).split(':')[-1]}/changes">${i.get_int_ini('unifield-%s-revno'%(br,))}</a> |
                % elif br != 'data' and i.get_int_ini('unifield-%s-revno'%(br, )) != r.revno[br]['revno']:
                        ${br}: <a href="https://bazaar.launchpad.net/~unifield-team/unifield-${br}/trunk/revision/${r.revno[br]['revno']}?compare_rev_id=${i.get_int_ini('unifield-%s-revno'%(br, ))}">@${i.get_ini('unifield-%s-revno'%(br, ))}</a> |
                % endif
            % endfor
            </td>
	</tr>
        % endfor
        <tr>
            <td colspan='3'><hr/></td>
        </tr>
        <tr>
            <td colspan='3'></td>
        </tr>
        </tbody>
        </table>
        </div>
        <div id="footer">
            <div class="content">
                <p><b>Last modification: ${r.now}.</b></p>
            </div>
        </div>
        <div class="comment">
        % for ic in set(r.state_icon.values()):
            <img  src="${r.icon_jira_dir}/${ic}">: ${','.join([x[0] for x in r.state_icon.items() if x[1] == ic])}
        % endfor
        <br />
        (to update the status run: <i>./runbot jira --jira-user user</i>)
        <div><span style="color:red">Red: UF number found in commit messages</span>, <span style="color:black">Black: UF number not found in commit</span></div>
        </div>
            % for br in ['wm', 'server', 'addons', 'web', 'data']:
            <div class="comment">
            <a href="${r.bzr_url}~unifield-team/unifield-${br}/trunk">${br}</a>: revno:${r.revno[br]['revno']} ${r.revno[br]['time']} 
            <div class="comment">
                ${r.revno[br]['lastmsg']}
            </div>
            </div>
            % endfor
        </div>
        </body>
        """
        self.now = time.strftime("%Y-%m-%d %H:%M:%S")
        return mako.template.Template(template).render(r=self,t=time.time(),re=re)

    def nginx_udpate(self):
        """ Update the link, port and entry of the new UniField instance into 2 files: nginx.conf and index.html
        """
        log("runbot-nginx-update")
        f=open(os.path.join(self.wd,'nginx','index.html'),"w")
        f.write(self.nginx_index())
        f.close()
        f=open(os.path.join(self.wd,'nginx','nginx.conf'),"w")
        f.write(self.nginx_config())
        f.close()
        self.nginx_reload()

    def _get_port(self):
        i = self.server_port
        while i in self.ports:
            i += 2
        return i

    def subdirs(self, dir):
        '''
        Retrieve the direct sub folders of the given folder 
        '''
        return [name for name in os.listdir(dir)
            if os.path.isdir(os.path.join(dir, name)) and not name.startswith('.')]

    def process_instances(self):
        ''' 
        Get the sub folders and build a list of instances to be run 
        '''
        self.ports = []
        for rbb in self.uf_instances.values():
            num_port = rbb.get_int_ini('port')
            if num_port:
                self.ports.append(num_port)
                self.ports.append(num_port+1)
        
        for rbb in self.uf_instances.values():
            if not rbb.get_int_ini('port'):
                new_port = self._get_port()
                self.ports.append(new_port)
                self.ports.append(new_port+1)
                rbb.set_ini('port', new_port)
            if rbb.get_bool_ini('start',True):
                rbb.start()
            
        self.nginx_udpate()

def skel(o, r):
    invalid_character = ['-']
        
    for char in invalid_character:
        if char in o.instance:
            raise Exception('\'%s\' is an invalid character in the name of the instance' % char)
    if o.instance == 'testjfb':
        sys.stderr.write("Stop au copier-coller des commandes !\nAu pire insere le caractere # avant de coller.\n") 
        sys.exit(1)

    if o.instance in r.uf_instances:
        sys.stderr.write("Error: %s exists\n"%(o.instance, ))
    else:
        new_folder = os.path.join(r.running_path, o.instance)
        os.mkdir(new_folder)
        new_ini = os.path.join(new_folder, 'config.ini')
        shutil.copy(r.common_configfile, new_ini)
        inf = open(r.common_configfile, 'r')
        outf = open(new_ini, "w")
        for line in inf:
            if line.startswith('comment'):
                outf.write("comment = %s\n"%(o.comment or ""))
            elif line.startswith('email'):
                outf.write("email = %s\n"%(o.email or ""))
            elif line.startswith('unifield-wm'):
                outf.write("unifield-wm = %s\n"%(o.unifield_wm or "link"))
            elif line.startswith('unifield-addons'):
                outf.write("unifield-addons = %s\n"%(o.unifield_addons or "link"))
            elif line.startswith('unifield-server'):
                outf.write("unifield-server = %s\n"%(o.unifield_server or "link"))
            elif line.startswith('unifield-web'):
                outf.write("unifield-web = %s\n"%(o.unifield_web or "link"))
            elif o.unit and line.startswith('load_demo'):
                outf.write("load_demo = 1\n")
            elif o.unit and line.startswith('load_data'):
                outf.write("load_data = 0\n")
            elif o.jira_id and line.startswith('jira-id'):
                outf.write("jira-id = %s\n"%(o.jira_id,))
            else:
                outf.write(line)

        inf.close()
        if o.start:
            outf.close()
            rbb = r.uf_instances.setdefault(o.instance, RunBotBranch(r,o.instance))
            rbb.init_folder()
            r.process_instances() 
        else:
            outf.write("start = 0")
            sys.stderr.write("Please edit %s , and change 'start',\nyou can use vi or a friendlier editor like nano\n"%(new_ini, ))
            outf.close()


def killall(o, r):
    for rbb in r.uf_instances.values():
        rbb.stop()
    
def kill_inst(o, r):
    if o.instance not in r.uf_instances:
        sys.stderr.write("%s not in instance\n"%o.instance)
    else:
        r.uf_instances[o.instance].stop()
    
def list_inst(o, r):
    sys.stderr.write("Nginx ")
    pid = r.is_nginx_running()
    if pid:
        sys.stderr.write("running on port: %s, pid: %s\n"%(r.nginx_port, pid))
    else:
        sys.stderr.write("isn't running\n")

    for rbb in r.uf_instances.values():
        sys.stderr.write("Instance %s:\n"%(rbb.name, ))
        if not rbb.get_bool_ini('start',True):
            sys.stderr.write("    Disabled in config.ini\n")
        sys.stderr.write("    web: %s\n"%(rbb.is_web_running() and 'running on port %s, pid %s'%(rbb.get_int_ini('port')+1, rbb.pidweb()) or 'not running', ))
        sys.stderr.write("    server: %s\n"%(rbb.is_server_running() and 'running on port %s, pid %s'%(rbb.get_int_ini('port'), rbb.pidserver()) or 'not running'))
    
def restartall(o, r):
    for rbb in r.uf_instances.values():
        rbb.stop()
    time.sleep(1)
    run_inst(o, r)

def run_inst(o, r):
    r.process_instances()
    
def restart(o, r):
    if o.instance not in r.uf_instances:
        sys.stderr.write("%s not in instance\n"%o.instance)
    else:
        r.uf_instances[o.instance].stop()
        run_inst(o, r)

def get_uf(o, r):
    for rbb in r.uf_instances.values():
        rbb.get_uf_from_log()


def jira_state(o, r):
    passwd = getpass.getpass('Jira Password : ')
    jira = jira_lib.Jira(o.jira_url, o.jira_user, passwd)
    icon_path = os.path.join(r.nginx_path, r.icon_jira_dir)
    jira_seen = []
    for rbb in r.uf_instances.values():
        all_uf = (rbb.get_ini('jira-id') or "").split(',')
        all_uf += (rbb.get_ini('detected-uf') or "").split(',')
        for uf in all_uf:
            if uf in jira_seen:
                continue
            dest = os.path.join(icon_path, '%s.gif'%(uf, ))
            os.path.exists(dest) and os.remove(dest)
            state = jira.get_state('UF-%s'%uf)
            icon = os.path.join(icon_path, r.state_icon.get(state, 'nok.gif'))
            os.symlink(icon, dest)
            jira_seen.append(uf)
    
    # Touch file to disable cache
    for ic in r.state_icon.values()+['nok.gif']:
        os.utime(os.path.join(icon_path, ic), None)

def del_inst(o, r):
    if o.instance not in r.uf_instances:
        sys.stderr.write("%s not in instance\n"%o.instance)
    else:
        r.uf_instances[o.instance].delete(o.only_db)
        run_inst(o, r)

def main():

    os.chdir(os.path.normpath(os.path.dirname(__file__)))
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--runbot-dir", metavar="DIR", default=".", help="runbot working dir (default: %(default)s)")
    parser.add_argument("--runbot-port", metavar="PORT", default=9200, help="starting port for servers (default: %(default)s)")
    parser.add_argument("--runbot-nginx-port", metavar="PORT", default=9100, help="starting port for nginx server (default: %(default)s)")
    parser.add_argument("--runbot-nginx-domain", metavar="DOMAIN", default="runbot.test.unifield.org", help="virtual host domain (default: %(default)s)")
    parser.add_argument("--debug", action="store_true", default=False, help="print debug on stdout (default: %(default)s)")
    parser.add_argument("--smtp-host", metavar="HOST", default='localhost', help="smtp server (default: %(default)s)")
    subparsers = parser.add_subparsers(dest='command')
    run_parser = subparsers.add_parser('run', help='start/init new instances')
    run_parser.set_defaults(func=run_inst)

    killall_parser = subparsers.add_parser('killall', help='kill all instances')
    killall_parser.set_defaults(func=killall)

    kill_parser = subparsers.add_parser('kill', help='kill an instance')
    kill_parser.add_argument('instance', action='store', help='instance to kill')
    kill_parser.set_defaults(func=kill_inst)
    
    restartall_parser = subparsers.add_parser('restartall', help='restart all instances')
    restartall_parser.set_defaults(func=restartall)

    restart_parser = subparsers.add_parser('restart', help='restart an instance')
    restart_parser.add_argument('instance', action='store', help='instance to kill')
    restart_parser.set_defaults(func=restart)
    
    list_parser = subparsers.add_parser('list', help='list all instances')
    list_parser.set_defaults(func=list_inst)
    
    jira = subparsers.add_parser('jira', help='update jira status')
    jira.add_argument('--jira-user', metavar='JIRA_USER', default='jfb', help='Jira User (default: %(default)s)')
    jira.add_argument('--jira-url', metavar='JIRA_URL', default='http://jira.unifield.org/', help='Jira url (default: %(default)s)')
    jira.set_defaults(func=jira_state)

    get_jira_id = subparsers.add_parser('get-uf', help='Get jira-id from commit messages')
    get_jira_id.set_defaults(func=get_uf)

    skel_parser = subparsers.add_parser('skel', help='create a directory for a new instance')
    skel_parser.add_argument('instance', action='store', help='instance')
    skel_parser.add_argument('--start', '-s', action='store_true', default=False, help='Start this instance')
    skel_parser.add_argument('--unit', action='store_true', default=False, help='Run instance with unit test (load demo)')
    skel_parser.add_argument('--unifield-wm', '-wm', metavar='URL', default='link', help='Launchpad url or keyword "link" (default: %(default)s)')
    skel_parser.add_argument('--unifield-addons', '-ad', metavar='URL', default='link', help='Launchpad url or keyword "link" (default: %(default)s)')
    skel_parser.add_argument('--unifield-server', '-se', metavar='URL', default='link', help='Launchpad url or keyword "link" (default: %(default)s)')
    skel_parser.add_argument('--unifield-web', '-we', metavar='URL', default='link', help='Launchpad url or keyword "link" (default: %(default)s)')
    skel_parser.add_argument('--comment', '-c')
    skel_parser.add_argument('--email', '-m')
    skel_parser.add_argument('--jira-id', '-j', help='List of jira-id (without UF-)')
    skel_parser.set_defaults(func=skel)
    
    delete_parser = subparsers.add_parser('delete', help='delete an instance')
    delete_parser.add_argument('instance', action='store', help='instance')
    delete_parser.add_argument("--only-db", action="store_true", default=False, help="delete the database and not the directory (default: delete db+directory)")
    delete_parser.set_defaults(func=del_inst)

    o = parser.parse_args()
    if (o.runbot_dir == '.'):
        o.runbot_dir = os.getcwd() #get the full path for the current working directory
    

    fsock = False
    if not o.debug:
        fsock = open('out.log', 'a')
        sys.stdout = fsock
    init = o.command == 'run'
    r = RunBot(o.runbot_dir, o.runbot_port, o.runbot_nginx_port, o.runbot_nginx_domain, init, o.smtp_host)
    o.func(o, r)
    if fsock:
        fsock.close()
    

if __name__ == '__main__':
    main()
