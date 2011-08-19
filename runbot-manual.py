#!/usr/bin/python

import cgitb,optparse,os,re,subprocess,sys,time
import fileinput
import launchpadlib.launchpad,mako.template
from lib import initdb
import threading


#----------------------------------------------------------
# OpenERP rdtools utils
#----------------------------------------------------------

def log(*l,**kw):
    out=[time.strftime("%Y-%m-%d %H:%M:%S")]
    for i in l:
        if not isinstance(i,basestring):
            i=repr(i)
        out.append(i)
    out+=["%s=%r"%(k,v) for k,v in kw.items()]
    print " ".join(out)

def lock(name):
    fd=os.open(name,os.O_CREAT|os.O_RDWR,0600)
    fcntl.lockf(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)

def nowait():
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)

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

        self.name = subfolder
        self.unique_name = subfolder
        self.project_name = subfolder
        self.uname=underscorize(self.unique_name)

        self.subdomain=subfolder
        self.instance_path=os.path.join(self.runbot.wd, "running", self.subdomain)

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

    def start_createdb(self,port):
        dbname = self.subdomain.lower()
        
#        run(["dropdb",dbname]) #there could be error if the db existed already, done by intention!
        run(["createdb",dbname]) #there could be error if the db existed already, done by intention!

    def start_run_server(self,port):
        log("branch-start-run-server", self.project_name, port=port)
        out=open(self.log_server_path,"w")
        
        config_file = os.path.join(self.instance_path,'etc', 'openerprc')

        
        dbname = self.subdomain.lower()
        cmd=[self.server_bin_path,"-c",config_file, "-d",dbname,"--no-xmlrpc","--no-xmlrpcs","--netrpc-port=%d"%(self.runbot.server_port+port)]

        if self.runbot.no_msf_profile:
            cmd += ['-i', 'base']
            self.runbot.load_data = False
        else:
            cmd += ['-i', 'msf_profile']

        if self.runbot.load_data:
            cmd.append("--without-demo=all")

        log("run",*cmd,log=self.log_server_path)
        p=subprocess.Popen(cmd, stdout=out, stderr=out, close_fds=True)
        self.running_server_pid=p.pid
    
        if self.runbot.load_data:
            pid = os.fork()
            if not pid:
                thread = threading.Thread(target=initdb.connect_db, args=('admin', 'admin', dbname, '127.0.0.1', self.runbot.server_port+port, self.data_path, self.runbot.nginx_path, self.name))
                thread.start()
                sys.exit(1)
        else:
            dest = os.path.join(self.runbot.nginx_path, '%s.png'%(self.name,))
            os.path.exists(dest) and os.remove(dest)
            os.symlink(os.path.join(self.runbot.nginx_path,'ok.png'), dest)


    def start_run_web(self,port):
        config="""
        [global]
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
        """%(self.runbot.web_port+port,self.runbot.server_port+port)
        config=config.replace("\n        ","\n")

	config_file = os.path.join(self.etc_path,"openerp-web.cfg")
        open(config_file,"w").write(config)

        out=open(self.log_web_path,"w")
        cmd=[self.web_bin_path, '-c', config_file]
        
        log("run",*cmd,log=self.log_web_path)
        p=subprocess.Popen(cmd, stdout=out, stderr=out, close_fds=True)
        self.running_web_pid=p.pid

    def start(self,port):
        log("branch-start",branch=self.unique_name,port=port)
        
        '''
        Here check if the instance existed already, then do not drop and recreate the DB, just launch the server and web!
        '''
        
        self.start_createdb(port)
        self.start_run_server(port)
        self.start_run_web(port)

        self.runbot.running.insert(0,self)
        self.runbot.running.sort(key=lambda x:x.date_last_modified,reverse=1)
        self.running_t0=time.time()
        self.running=True
        self.running_port=port

    def stop(self):
        log("branch-stop",branch=self.unique_name,port=self.running_port)
        kill(self.running_server_pid)
        kill(self.running_web_pid)
        self.runbot.running.remove(self)
        self.running=False
        self.running_port=None

class RunBot(object):
    def __init__(self,wd,server_port,web_port,nginx_port,domain, load_data, no_msf_profile):
        self.wd=wd
        self.common_path=os.path.join(self.wd,"common")
        self.server_port=int(server_port)
        self.web_port=int(web_port)
        self.nginx_port=int(nginx_port)
        self.domain=domain
        self.uf_instances={}
        self.now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.running=[]
        self.load_data = load_data
        self.no_msf_profile = no_msf_profile
	self.nginx_path = os.path.join(self.wd,'nginx')

    def nginx_reload(self):
        nginx_path = os.path.join(self.wd,'nginx')
        nginx_pid_path = os.path.join(nginx_path,'nginx.pid')
        if os.path.isfile(nginx_pid_path):
            pid=int(open(nginx_pid_path).read())
            os.kill(pid,1)
        else:
            run(["nginx","-p", self.wd + "/", "-c", os.path.join(nginx_path,"nginx.conf")])

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
                location / { proxy_pass http://127.0.0.1:${r.web_port+i.running_port}; proxy_set_header X-Forwarded-Host $host; }
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
        % for i in r.running:
        <tr class="file">
            <td class="name left">
                <a href="http://${i.subdomain}.${r.domain}/"  target="_blank">${i.subdomain}</a> <small>(netrpc: ${r.server_port+i.running_port})</small> <img src="${i.subdomain}.png" alt=""/>
                <br>
            </td>
            <td class="date">
                % if t-i.running_t0 < 120:
                    <span style="color:red;">${r.now}</span>
                % else:
                    <span style="color:green;">${r.now}</span>
                % endif
            </td>
            <td>
                <a href="http://${r.domain}/${i.subdomain}/logs/server.txt">server</a>
                <a href="http://${r.domain}/${i.subdomain}/logs/web.txt">web</a>
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

    def allocate_port_and_run(self,rbb):
        if len(self.running) >= 100:
            victim = self.running[-1]
            victim.stop()
        running_ports=[i.running_port for i in self.running]
        for p in range(100):
            if p not in running_ports:
                break

        rbb.start(p)
        #self.nginx_udpate()

    def subdirs(self, dir):
        '''
        Retrieve the direct sub folders of the given folder 
        '''
        return [name for name in os.listdir(dir)
            if os.path.isdir(os.path.join(dir, name))]

    def process_instances(self):
        log("runbot-folder")

        ''' 
        Get the sub folders and build a list of instances to be run 
        '''
        self.kill_runbot_processes() # this is currently not working
        running_path=os.path.join(self.wd, "running")
        allsubdirs = self.subdirs(running_path) # in consumption that the sub-folder NAMES are valid

        for folder in allsubdirs:
            rbb=self.uf_instances.setdefault(folder, RunBotBranch(self,folder))
            '''
            Check if the current instance is running, then stop it and rebuild, restart the instance
            '''
            if rbb.running:
                rbb.stop()
            else: 
                self.init_folder(folder) # create some necessary files and folder
                 
            self.allocate_port_and_run(rbb)
            
        self.nginx_udpate()

    def kill_runbot_processes(self):
        running_path = os.path.join(self.wd,'running')
        kill_script = os.path.join(self.wd, 'kill.sh')
        cmd = ["/bin/sh",  kill_script, running_path]
        
        log("kill all running process of runbot")
        out=open(os.path.join(self.wd,'nginx','access.log'),"w")
        
        #WHY IT IS NOT WORKING HERE?????
        p=subprocess.Popen(cmd, stdout=out, stderr=out, close_fds=True)

        
    def init_folder(self, folder):

        ''' To do the following things if not exist
            - create the logs folder for storing log files
            - create soft-link to: unifield-server, unifield-addons, unifield-web if not exist (in case no change has been made)
        '''
        instance_path=os.path.join(self.wd, "running", folder)
        
        logs_dir = os.path.join(instance_path, "logs")
        if not os.path.exists(logs_dir):
            os.mkdir(logs_dir)

        # copy the unifield-server project from 'common' folder if not existed
        #self.copy_project(instance_path, "unifield-server")
        #self.copy_project(instance_path, "unifield-web")
	self.create_softlink(instance_path, "unifield-server")
	self.create_softlink(instance_path, "unifield-web")
        # copy the folder 'etc' from 'common' folder, then fill the instance path
        self.process_folder_etc(instance_path, folder)

        # create softlinks for these 3 projects if not existed
        self.create_softlink(instance_path, "unifield-addons")
        self.create_softlink(instance_path, "unifield-wm")
        self.create_softlink(instance_path, "unifield-data")


    def process_folder_etc(self, instance_path, folder):
        # delete and recopy the folder "etc"
        project_path = os.path.join(instance_path, "etc")
        run(["rm","-r", project_path]) # delete first
        
        common_etc_path = os.path.join(self.common_path, "etc")
        run(["cp","-r", common_etc_path, instance_path])
        
        # replace the UF_ADDONS_PATH with the modules path of the current instance 
        config_file = os.path.join(project_path, 'openerprc')
        for line in fileinput.FileInput(config_file, inplace=1):
            line = line.replace("UF_ADDONS_PATH", instance_path)
            line = line.replace("UF_INSTANCE", folder)
            print line

    def copy_project(self, instance_path, project_name):
        # create soft-link for unifield-XXX
        project_path = os.path.join(instance_path, project_name)
        if not os.path.exists(project_path):
            common_project_path = os.path.join(self.common_path, project_name)
            run(["cp","-r", common_project_path, instance_path])

    def create_softlink(self, instance_path, project_name):
        project_path = os.path.join(instance_path, project_name)
        if not os.path.exists(project_path):
            common_project_path = os.path.join(self.common_path, project_name)
            run(["ln","-s", common_project_path, project_path])

    def create_softlink_modules(self, instance_path, project_name):
        # create soft-link of modules to unifield-server/bin/addons
        project_path = os.path.join(instance_path, project_name)
        server_addons_path = os.path.join(instance_path, "unifield-server", "bin", "addons")
        
        # if this module path does not exist in the current folder, then make a softlink to the one in common folder
        if not os.path.exists(project_path):
            project_path = os.path.join(self.common_path, project_name)
            
        project_path = os.path.join(project_path, "*")
        run(["ln","-s", server_addons_path, project_path])

def main():

    os.chdir(os.path.normpath(os.path.dirname(__file__)))
    parser = optparse.OptionParser(usage="%prog [--runbot-init|--runbot-run] [options] ",version="1.0")
    parser.add_option("--runbot-init", action="store_true", help="initialize the runbot environment")
    parser.add_option("--runbot-run", action="store_true", help="run the runbot")
    parser.add_option("--runbot-dir", metavar="DIR", default=".", help="runbot working dir (%default)")
    parser.add_option("--runbot-server-port", metavar="PORT", default=9200, help="starting port for servers (%default)")
    parser.add_option("--runbot-web-port", metavar="PORT", default=9300, help="starting port for web (%default)")
    parser.add_option("--runbot-nginx-port", metavar="PORT", default=9100, help="starting port for nginx server (%default)")
    parser.add_option("--runbot-nginx-domain", metavar="DOMAIN", default="runbot.unifield.org", help="virtual host domain (%default)")
    parser.add_option("--load-data", default=True, action="store_false", help="load unifield data")
    parser.add_option("--only-base", default=False, action="store_true", help="don't load msf_profile")
    
    o, a = parser.parse_args(sys.argv)
    if (o.runbot_dir == '.'):
        o.runbot_dir = os.getcwd() #get the full path for the current working directory

    # first, kill all processes running previously by Runbot
    running_path=os.path.join(o.runbot_dir, "running")
    print "kill `ps faux | grep " + running_path + " | awk '{print $2}' `"
    
    r = RunBot(o.runbot_dir,o.runbot_server_port,o.runbot_web_port,o.runbot_nginx_port,o.runbot_nginx_domain, o.load_data, o.only_base)
    r.process_instances()

if __name__ == '__main__':
    main()
