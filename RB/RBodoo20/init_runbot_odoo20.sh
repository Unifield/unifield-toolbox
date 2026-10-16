#!/bin/bash

set -o errexit -o pipefail -o nounset

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rb_server_url="rb.unifield.org"
MAILTO=""
PYTHON_EXE="python3"
[[ -x /opt/python-3.13/bin/python3 ]] && PYTHON_EXE="/opt/python-3.13/bin/python3"
ODOO_REPO="https://github.com/odoo/odoo.git"
ODOO_BRANCH="20.0"
CERTBOT_BIN="certbot"
WEBROOT="/var/www"
PG_MODE="auto"
PG_SYS_USER="postgres"
PG_SHARED_PORT="5432"
PG_BIN=""
EXTRA_PIP="numpy pypdfium2"
DEFAULT_ADMIN_PASSWD="Only4RB!"
ADMIN_PASSWD="${RB_ADMIN_PASSWD:-$DEFAULT_ADMIN_PASSWD}"
MASTER_PASSWD="${RB_MASTER_PASSWD:-}"
ADDONS_GIT_USER=""
ADDONS_GIT_TOKEN=""

ADDONS_REPO="none"; ADDONS_BRANCH=""; MODULES=""; EXTRA_DIR=""
WITH_SSL="Yes"; WITH_DEMO=""; LANG_LOAD="fr_FR"; WORKERS=0; RB_PREFIX=""
DBMGR=1; DRY=0; MODULES_SET=0

usage() {
cat <<EOF
Usage: $0 [options] NAME
  -d           DRY RUN: print what would be done, write/execute nothing
  -b BRANCH    Odoo branch (default: $ODOO_BRANCH)
  -g URL       Odoo git repo (default: $ODOO_REPO)
  -a URL       git repo of your modules (default: none = Odoo only)
  -B BRANCH    branch of your modules (default: repo default branch)
  -m LIST      modules to install, comma-separated (default: base)
  -n           no SSL (http only)
  -h           this help
EOF
exit 1
}

while getopts db:g:a:B:m:nh opt; do
  case $opt in
    d) DRY=1 ;;
    b) ODOO_BRANCH=$OPTARG ;;
    g) ODOO_REPO=$OPTARG ;;
    a) ADDONS_REPO=$OPTARG ;;
    B) ADDONS_BRANCH=$OPTARG ;;
    m) MODULES=$OPTARG; MODULES_SET=1 ;;
    n) WITH_SSL="No" ;;
    *) usage ;;
  esac
done
[[ "$ADDONS_REPO" == "none" ]] && ADDONS_REPO=""
[[ -n "$MODULES" ]] || MODULES="base"
shift $((OPTIND - 1))

say()  { echo "== $*"; }
warn() { echo "WARNING: $*" >&2; }
die()  { echo "ERROR: $*" >&2; exit 1; }
run()  { if (( DRY )); then echo "[dry] $*"; else "$@"; fi; }
mask() { sed -E -e 's/((passwd|password|PASSWD|PW)[A-Za-z_]* *[=:] *).*/\1********/' -e 's/^(Master password.*: ).*/\1********/' -e 's/^(Per-action passwords: ).*/\1********/'; }

as_user() {
  if (( DRY )); then echo "[dry] (as $USERERP) $*"; return 0; fi
  ( cd "$HOME_DIR" && runuser -u "$USERERP" -- env HOME="$HOME_DIR" "$@" )
}
write_file() {
  local f=$1 mode=${2:-644} owner=${3:-root:root}
  if (( DRY )); then echo "[dry] would write $f ($mode $owner):"; mask | sed 's/^/    | /'; return 0; fi
  cat > "$f"; chmod "$mode" "$f"; chown "$owner" "$f"
}
gen_pw() { openssl rand -base64 24 | tr -d '/+=\n' | cut -c1-16; }
b64()    { printf '%s' "$1" | base64 -w0; }
port_busy() { command -v ss >/dev/null || return 1; ss -ltnH | awk '{print $4}' | grep -qE "[:.]$1\$"; }

(( DRY )) || [[ $EUID -eq 0 ]] || die "Must be run as root (or use -d for a dry run)"
[[ -n "${1:-}" ]] || { echo "A name is required, e.g. odoo20-demo"; usage; }
[[ "$PG_MODE" =~ ^(auto|private|shared)$ ]] || die "-S must be auto, private or shared"

REV="$1"
[[ -n "$RB_PREFIX" ]] && REV="${RB_PREFIX}-${REV}"
REV=${REV,,}; REV=${REV//[^a-z0-9-]/-}
[[ "$REV" =~ ^[a-z][a-z0-9-]{1,28}[a-z0-9]$ ]] || die "Invalid name ('$REV'): 3-30 chars, letters/digits/-, must start with a letter"
case "$REV" in root|postgres|www-data|daemon|bin|sys|ubuntu|admin|odoo) die "Reserved name: $REV" ;; esac
USERERP="$REV"; DBNAME="${REV//-/_}"; HOME_DIR="/home/$USERERP"
DOMAIN="${USERERP}.${rb_server_url}"
PROTO="http"; [[ "$WITH_SSL" == "Yes" ]] && PROTO="https"
[[ "$MODULES" =~ ^[A-Za-z0-9_,]+$ ]] || die "-m: invalid module list"
[[ -z "$EXTRA_DIR" || -d "$EXTRA_DIR" ]] || die "-e: folder not found: $EXTRA_DIR"

if id "$USERERP" >/dev/null 2>&1; then die "User '$USERERP' already exists. I never touch an existing user."; fi
[[ -e "$HOME_DIR" ]] && die "$HOME_DIR already exists"
[[ -e "/etc/apache2/sites-available/${USERERP}.conf" ]] && die "An apache vhost ${USERERP}.conf already exists"
[[ -e "/etc/systemd/system/${USERERP}-server.service" ]] && die "A service ${USERERP}-server already exists"

command -v "$PYTHON_EXE" >/dev/null || die "$PYTHON_EXE not found (see -P)"
"$PYTHON_EXE" -c 'import sys; assert sys.version_info >= (3,10), sys.version' || die "Python >= 3.10 required (see -P)"
"$PYTHON_EXE" -c 'import venv, ensurepip' 2>/dev/null || die "$PYTHON_EXE has no venv/ensurepip module"
command -v git >/dev/null || die "git is missing"
if (( ! DRY )); then
  for c in runuser systemctl apachectl a2ensite visudo ss openssl; do command -v "$c" >/dev/null || die "missing command: $c"; done
  [[ "$WITH_SSL" == "Yes" ]] && { command -v "$CERTBOT_BIN" >/dev/null || die "certbot not found (or use -n for http only)"; }
fi

if (( DRY )); then userid=$(awk -F: '$3>=1000 && $3<6000 && $3>m{m=$3} END{print (m?m:1999)+1}' /etc/passwd); else userid=""; fi

pg_bin_ge16() {
  local d v
  [[ -n "$PG_BIN" ]] && { echo "$PG_BIN"; return; }
  for d in $(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | sort -t/ -k5 -n -r); do
    v=$(basename "$(dirname "$d")"); (( v >= 16 )) && [[ -x "$d/initdb" ]] && { echo "$d"; return; }
  done
}
shared_pg_version() {
  (( DRY )) && { echo ""; return; }
  runuser -u "$PG_SYS_USER" -- psql -p "$PG_SHARED_PORT" -Atc 'show server_version_num' 2>/dev/null || true
}
if [[ "$PG_MODE" == "auto" ]]; then
  sv=$(shared_pg_version)
  if [[ -n "$sv" && "$sv" -ge 160000 ]]; then PG_MODE=shared
  elif [[ -n "$(pg_bin_ge16)" ]]; then PG_MODE=private
  elif (( DRY )); then PG_MODE=private
  else die "Odoo 20 needs PostgreSQL >= 16: shared cluster too old/unreachable and no PG>=16 in /usr/lib/postgresql (see PG_BIN in ~/RBconfig)"; fi
fi
if [[ "$PG_MODE" == "private" ]]; then
  PG_BIN="$(pg_bin_ge16)"
  if [[ -z "$PG_BIN" ]]; then (( DRY )) && PG_BIN="/usr/lib/postgresql/18/bin" || die "No PG>=16 found (PG_BIN)"; fi
  (( DRY )) || [[ -x "$PG_BIN/initdb" ]] || die "$PG_BIN/initdb not found"
fi

if (( ! DRY )); then
  mkdir -p "$SCRIPT_DIR/LOG"; LOGFILE="$SCRIPT_DIR/LOG/$REV.log"; : > "$LOGFILE"
  exec > >(tee -a "$LOGFILE") 2>&1
fi
send_mail() {
  [[ -n "$MAILTO" ]] && command -v mail >/dev/null || return 0
  { mask < "$HOME_DIR/RB_info.txt" 2>/dev/null; echo "-----"; mask < "$LOGFILE"; } \
    | mail -a 'Content-Type: text/plain' -s "RB ${REV} $1" "$MAILTO" || true
}
STARTED=0
on_exit() {
  local rc=$?
  (( DRY )) && return 0
  if (( rc != 0 )); then
    echo; echo "FAILED (code $rc) while creating '$REV'."
    if (( STARTED )); then echo "Nothing was removed automatically. To clean up:  $SCRIPT_DIR/rm_runbot_odoo.sh $REV"; fi
    send_mail FAILED
  else send_mail OK; fi
}
trap on_exit EXIT

(( DRY )) && echo "######## DRY RUN: nothing is executed ########"

say "Creating user $USERERP"
STARTED=1
run useradd -s /bin/bash -d "$HOME_DIR" -m "$USERERP"
if (( ! DRY )); then
  userid=$(id -u "$USERERP")
  chmod 750 "$HOME_DIR"
fi

{
  echo "REV=$REV"; echo "PG_MODE=$PG_MODE"; echo "PG_SHARED_PORT=$PG_SHARED_PORT"; echo "PG_SYS_USER=$PG_SYS_USER"
  echo "DOMAIN=$DOMAIN"; echo "WITH_SSL=$WITH_SSL"; echo "CREATED=$(date -Is)"
} | write_file "$HOME_DIR/.runbot_odoo" 644 "$USERERP:$USERERP"
(( userid >= 1000 )) || die "uid $userid < 1000: refusing"
HTTPPORT=$((userid * 10 + 2)); GEVENTPORT=$((userid * 10 + 4)); PGPORT_RB=$((userid * 10 + 5))
(( PGPORT_RB < 65535 )) || die "uid $userid too large for the uid*10+k port scheme"
for p in $HTTPPORT $GEVENTPORT; do port_busy "$p" && die "Port $p already in use"; done
[[ "$PG_MODE" == "private" ]] && { port_busy "$PGPORT_RB" && die "Port $PGPORT_RB already in use"; }
echo "   ports: http=$HTTPPORT  gevent=$GEVENTPORT  private-pg=$PGPORT_RB   (PostgreSQL: $PG_MODE)"

[[ -n "$ADMIN_PASSWD"  ]] || ADMIN_PASSWD=$(gen_pw)
[[ -n "$MASTER_PASSWD" ]] || MASTER_PASSWD=$(gen_pw)
DROP_PW=$(gen_pw); BKP_PW=$(gen_pw); RESTORE_PW=$(gen_pw)
[[ "$MASTER_PASSWD" == "admin" ]] && die "The master password cannot be 'admin' (Odoo refuses it)"

git_clone() {
  local url=$1 dest=$2; shift 2
  local gu="" gt="" askpass="" genv=(GIT_TERMINAL_PROMPT=0)
  if (( ! DRY )) && [[ -t 0 && "$url" == https://* && "$url" != "https://github.com/odoo/odoo.git" ]]; then
    read -r -p "Git username for $url (empty = anonymous): " gu
    if [[ -n "$gu" ]]; then read -r -s -p "Git token/password (hidden): " gt; echo; fi
  fi
  if [[ -n "$gt" ]]; then
    askpass=$(mktemp /tmp/rb_askpass.XXXXXX)
    cat > "$askpass" <<'EOS'
#!/bin/sh
case "$1" in Username*) printf '%s\n' "$RB_GIT_USER" ;; *) printf '%s\n' "$RB_GIT_TOKEN" ;; esac
EOS
    chmod 755 "$askpass"
    export RB_GIT_USER="$gu" RB_GIT_TOKEN="$gt"
    genv+=(GIT_ASKPASS="$askpass")
    echo "   (git credentials for user '$gu' passed via GIT_ASKPASS)"
  fi
  as_user env "${genv[@]}" git clone "$@" "$url" "$dest" || { [[ -n "$askpass" ]] && rm -f "$askpass"; unset RB_GIT_USER RB_GIT_TOKEN; return 1; }
  [[ -n "$askpass" ]] && rm -f "$askpass"
  unset RB_GIT_USER RB_GIT_TOKEN
}

say "Cloning sources"
git_clone "$ODOO_REPO" odoo -b "$ODOO_BRANCH"
if (( DRY )); then
  echo "[dry] if ~/odoo/.gitmodules exists: rewrite git@github.com: to https://github.com/, then git submodule sync + update --init --recursive"
elif [[ -f "$HOME_DIR/odoo/.gitmodules" ]]; then
  say "Git submodules"
  as_user sed -i 's|git@github.com:|https://github.com/|g' "$HOME_DIR/odoo/.gitmodules"
  as_user env -C "$HOME_DIR/odoo" git submodule sync
  as_user env -C "$HOME_DIR/odoo" git submodule update --init --recursive
fi
REPO_DIR="$HOME_DIR/odoo"
ODOO_SRC="$REPO_DIR"
if (( ! DRY )); then
  if [[ -f "$REPO_DIR/odoo-bin" ]]; then ODOO_SRC="$REPO_DIR"
  elif [[ -f "$REPO_DIR/odoo/odoo-bin" ]]; then ODOO_SRC="$REPO_DIR/odoo"
  else die "odoo-bin not found in ~/odoo nor ~/odoo/odoo: unexpected layout of $ODOO_REPO (ls $REPO_DIR)"; fi
  echo "   Odoo sources: $ODOO_SRC"
fi
if [[ -n "$ADDONS_REPO" ]]; then
  ADDONS_ARGS=()
  [[ -n "$ADDONS_BRANCH" ]] && ADDONS_ARGS+=(-b "$ADDONS_BRANCH")
  git_clone "$ADDONS_REPO" custom-addons "${ADDONS_ARGS[@]}"
fi
as_user mkdir -p etc log data
if [[ -n "$EXTRA_DIR" ]]; then
  say "Local test addons ($EXTRA_DIR -> ~/test-addons)"
  as_user mkdir -p test-addons
  run cp -a "$EXTRA_DIR"/. "$HOME_DIR/test-addons/"
  run chown -R "$USERERP:$USERERP" "$HOME_DIR/test-addons"
fi

say "Virtualenv + Python dependencies"
as_user "$PYTHON_EXE" -m venv venv
as_user venv/bin/pip install -q -U pip wheel setuptools
if (( DRY )); then echo "[dry] pip install -r requirements.txt of the Odoo sources (without psycopg2) + psycopg2-binary"
else
  REQ_SRC="$ODOO_SRC/requirements.txt"
  [[ -s "$REQ_SRC" ]] || REQ_SRC="$REPO_DIR/requirements.txt"
  [[ -s "$REQ_SRC" ]] || die "requirements.txt not found in $ODOO_SRC nor $REPO_DIR"
  grep -viE '^\s*psycopg2' "$REQ_SRC" > "$HOME_DIR/.req_odoo.txt"
  chown "$USERERP:$USERERP" "$HOME_DIR/.req_odoo.txt"
  as_user venv/bin/pip install -r .req_odoo.txt
  as_user venv/bin/pip install psycopg2-binary
  rm -f "$HOME_DIR/.req_odoo.txt"
  if [[ "$ODOO_SRC" != "$REPO_DIR" && -s "$REPO_DIR/requirements.txt" ]]; then
    say "Python dependencies of the repo (requirements.txt at its root)"
    grep -viE '^\s*psycopg2' "$REPO_DIR/requirements.txt" > "$HOME_DIR/.req_repo.txt"
    chown "$USERERP:$USERERP" "$HOME_DIR/.req_repo.txt"
    as_user venv/bin/pip install -r .req_repo.txt || warn "requirements.txt of the repo: partial failure"
    rm -f "$HOME_DIR/.req_repo.txt"
  fi
  if [[ -f "$HOME_DIR/custom-addons/requirements.txt" ]]; then
    as_user venv/bin/pip install -r custom-addons/requirements.txt || warn "requirements.txt of your modules: partial failure"
  fi
  SCAN_ROOTS=("$HOME_DIR/custom-addons" "$HOME_DIR/test-addons")
  if [[ "$ODOO_SRC" != "$REPO_DIR" ]]; then SCAN_ROOTS+=("$REPO_DIR"); [[ -d "$REPO_DIR/addons" ]] && SCAN_ROOTS+=("$REPO_DIR/addons"); fi
  DEPS=$("$PYTHON_EXE" -I - "${SCAN_ROOTS[@]}" <<'PY' 2>/dev/null || true
import ast, os, sys
m = {"PIL": "Pillow", "yaml": "PyYAML", "cv2": "opencv-python-headless", "dateutil": "python-dateutil"}
out = set()
for root in sys.argv[1:]:
    if not os.path.isdir(root): continue
    for d in os.listdir(root):
        p = os.path.join(root, d, "__manifest__.py")
        if os.path.isfile(p):
            try:
                deps = ast.literal_eval(open(p).read()).get("external_dependencies", {}).get("python", [])
            except Exception:
                continue
            out.update(m.get(x, x) for x in deps)
print(" ".join(sorted(out)))
PY
)
  for pkg in $DEPS $EXTRA_PIP; do
    as_user venv/bin/pip install -q "$pkg" || warn "pip install $pkg failed"
  done
fi

say "PostgreSQL ($PG_MODE)"
PGENV_HOST=""; PGENV_PORT=""
if [[ "$PG_MODE" == "private" ]]; then
  PGSOCK="$HOME_DIR/pgsock"; PGDATA="$HOME_DIR/pgdata"
  as_user mkdir -p pgsock
  as_user "$PG_BIN/initdb" -D "$PGDATA" -U "$USERERP" --auth-local=peer --auth-host=reject -E UTF8 --locale=C.UTF-8
  write_file "$HOME_DIR/pgdata/postgresql.auto.conf" 600 "$USERERP:$USERERP" <<EOF
listen_addresses = ''
port = $PGPORT_RB
unix_socket_directories = '$PGSOCK'
unix_socket_permissions = 0700
EOF
  write_file "/etc/systemd/system/${USERERP}-pg.service" 644 <<EOF
[Unit]
Description=Private PostgreSQL of runbot $USERERP
After=network.target

[Service]
Type=simple
User=$USERERP
Group=$USERERP
ExecStart=$PG_BIN/postgres -D $PGDATA
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
  PGENV_HOST="$PGSOCK"; PGENV_PORT="$PGPORT_RB"
  run systemctl daemon-reload
  run systemctl enable --now "${USERERP}-pg"
  if (( ! DRY )); then
    for _ in $(seq 1 30); do "$PG_BIN/pg_isready" -q -h "$PGSOCK" -p "$PGPORT_RB" && break; sleep 1; done
    "$PG_BIN/pg_isready" -q -h "$PGSOCK" -p "$PGPORT_RB" || die "Private PostgreSQL does not start (journalctl -u ${USERERP}-pg)"
  fi
else
  PGENV_PORT="$PG_SHARED_PORT"
  if (( DRY )); then echo "[dry] createuser -p $PG_SHARED_PORT -S -R -d $USERERP (as $PG_SYS_USER; NO DROP ROLE)"
  else
    runuser -u "$PG_SYS_USER" -- psql -p "$PG_SHARED_PORT" -Atc "select 1 from pg_roles where rolname='$USERERP'" | grep -q 1 \
      && die "PostgreSQL role $USERERP already exists: not overwriting it"
    runuser -u "$PG_SYS_USER" -- createuser -p "$PG_SHARED_PORT" -S -R -d "$USERERP"
  fi
fi

say "odoo.conf"
ADDONS_PATH="$ODOO_SRC/addons,$ODOO_SRC/odoo/addons"
if [[ "$ODOO_SRC" != "$REPO_DIR" ]]; then
  compgen -G "$REPO_DIR/*/__manifest__.py" >/dev/null && ADDONS_PATH="$ADDONS_PATH,$REPO_DIR"
  [[ -d "$REPO_DIR/addons" ]] && ADDONS_PATH="$ADDONS_PATH,$REPO_DIR/addons"
fi
if [[ -n "$ADDONS_REPO" ]]; then
  ADDONS_PATH="$ADDONS_PATH,$HOME_DIR/custom-addons"
  [[ -d "$HOME_DIR/custom-addons/addons" ]] && ADDONS_PATH="$ADDONS_PATH,$HOME_DIR/custom-addons/addons"
fi
[[ -n "$EXTRA_DIR" ]] && ADDONS_PATH="$ADDONS_PATH,$HOME_DIR/test-addons"

SERVER_WIDE="base,web"
HAVE_PWMOD=0
if (( DBMGR )); then
  if (( DRY )) || [[ -d "$HOME_DIR/custom-addons/msf_db_manager_passwords" || -d "$HOME_DIR/test-addons/msf_db_manager_passwords" ]]; then
    HAVE_PWMOD=1; SERVER_WIDE="$SERVER_WIDE,msf_db_manager_passwords"
  else warn "module msf_db_manager_passwords missing: no per-action passwords (only the master password protects)"; fi
fi

{
  echo "[options]"
  echo "admin_passwd = $MASTER_PASSWD"
  echo "db_user = $USERERP"
  [[ -n "$PGENV_HOST" ]] && echo "db_host = $PGENV_HOST"
  [[ "$PG_MODE" == "private" || "$PG_SHARED_PORT" != "5432" ]] && echo "db_port = $PGENV_PORT"
  echo "addons_path = $ADDONS_PATH"
  echo "data_dir = $HOME_DIR/data"
  echo "http_port = $HTTPPORT"
  (( WORKERS > 0 )) && echo "gevent_port = $GEVENTPORT"
  echo "proxy_mode = True"
  echo "workers = $WORKERS"
  echo "logfile = $HOME_DIR/log/odoo.log"
  if (( DBMGR )); then
    echo "list_db = True"
    echo "dbfilter = ^${DBNAME}.*\$"
    echo "server_wide_modules = $SERVER_WIDE"
    if (( HAVE_PWMOD )); then
      echo "dropdb_passwd = $(b64 "$DROP_PW")"
      echo "bkpdb_passwd = $(b64 "$BKP_PW")"
      echo "restoredb_passwd = $(b64 "$RESTORE_PW")"
    fi
  else
    echo "db_name = $DBNAME"
    echo "list_db = False"
    echo "dbfilter = ^${DBNAME}\$"
  fi
} | write_file "$HOME_DIR/etc/odoo.conf" 600 "$USERERP:$USERERP"

{
  echo '#!/bin/bash'
  echo '. ~/venv/bin/activate'
  [[ -n "$PGENV_HOST" ]] && echo "export PGHOST=$PGENV_HOST"
  echo "export PGPORT=$PGENV_PORT"
  echo "if [ \"\$1\" = \"shell\" ]; then shift; exec python $ODOO_SRC/odoo-bin shell -c ~/etc/odoo.conf \"\$@\"; fi"
  echo "exec python $ODOO_SRC/odoo-bin -c ~/etc/odoo.conf \"\$@\""
} | write_file "$HOME_DIR/odoo.sh" 755 "$USERERP:$USERERP"

say "systemd service"
{
  echo "[Unit]"
  echo "Description=Odoo runbot $USERERP"
  if [[ "$PG_MODE" == "private" ]]; then echo "After=network.target ${USERERP}-pg.service"; echo "Requires=${USERERP}-pg.service"
  else echo "After=network.target postgresql.service"; fi
  echo
  echo "[Service]"
  echo "Type=simple"
  echo "User=$USERERP"
  echo "Group=$USERERP"
  echo "WorkingDirectory=$ODOO_SRC"
  [[ -n "$PGENV_HOST" ]] && echo "Environment=PGHOST=$PGENV_HOST"
  echo "Environment=PGPORT=$PGENV_PORT"
  echo "ExecStart=$HOME_DIR/venv/bin/python $ODOO_SRC/odoo-bin -c $HOME_DIR/etc/odoo.conf"
  echo "Restart=on-failure"
  echo
  echo "[Install]"
  echo "WantedBy=multi-user.target"
} | write_file "/etc/systemd/system/${USERERP}-server.service" 644
run systemctl daemon-reload
run systemctl enable "${USERERP}-server"

SYSTEMCTL=$(command -v systemctl || echo /bin/systemctl)
SUDO_TMP=$(mktemp)
{
  for u in server $([[ "$PG_MODE" == "private" ]] && echo pg); do
    for a in start stop restart; do echo "$USERERP ALL=(ALL) NOPASSWD:$SYSTEMCTL $a $USERERP-$u"; done
  done
} > "$SUDO_TMP"
if (( DRY )); then echo "[dry] sudoers /etc/sudoers.d/99-$USERERP:"; sed 's/^/    | /' "$SUDO_TMP"
else
  visudo -cf "$SUDO_TMP" >/dev/null || die "generated sudoers is invalid, aborting (nothing installed)"
  install -m 0440 -o root -g root "$SUDO_TMP" "/etc/sudoers.d/99-$USERERP"
fi
rm -f "$SUDO_TMP"

say "Initializing database $DBNAME (modules: $MODULES)"
INIT_ARGS=(-d "$DBNAME" -i "$MODULES" --stop-after-init)
[[ -z "$WITH_DEMO" ]] && INIT_ARGS+=(--without-demo=True)
[[ "$LANG_LOAD" != "none" ]] && INIT_ARGS+=(--load-language="$LANG_LOAD")
as_user ./odoo.sh "${INIT_ARGS[@]}"

say "Admin user password + web.base.url"
if (( DRY )); then echo "[dry] odoo shell: admin.write(password); ir.config_parameter web.base.url=$PROTO://$DOMAIN"
else
  export RB_ADMIN_PW="$ADMIN_PASSWD"
  as_user ./odoo.sh shell -d "$DBNAME" <<EOF
u = env['res.users'].search([('login', '=', 'admin')], limit=1)
u.write({'password': __import__('os').environ['RB_ADMIN_PW']})
P = env['ir.config_parameter'].sudo()
rec = P.search([('key', '=', 'web.base.url')], limit=1)
if rec:
    rec.write({'value': '$PROTO://$DOMAIN'})
else:
    P.create({'key': 'web.base.url', 'value': '$PROTO://$DOMAIN'})
env.cr.commit()
print('ADMIN_PW_OK', u.id)
EOF
  unset RB_ADMIN_PW
fi

say "Starting the Odoo server"
run systemctl start "${USERERP}-server"
if (( ! DRY )); then
  for _ in $(seq 1 40); do ss -ltnH | awk '{print $4}' | grep -qE "[:.]$HTTPPORT\$" && break; sleep 1; done
  port_busy "$HTTPPORT" || { tail -n 30 "$HOME_DIR/log/odoo.log" 2>/dev/null; die "Odoo is not listening on $HTTPPORT (journalctl -u ${USERERP}-server)"; }
fi

say "Apache"
run a2enmod proxy proxy_http proxy_wstunnel rewrite headers ssl
VHOST="/etc/apache2/sites-available/${USERERP}.conf"
WSPORT=$HTTPPORT; (( WORKERS > 0 )) && WSPORT=$GEVENTPORT
proxy_block() {
cat <<EOF
    ProxyPreserveHost On
    ProxyRequests Off
    ProxyTimeout 2000
    SetEnv proxy-nokeepalive 1
    ErrorLog /var/log/apache2/${USERERP}-error.log
    CustomLog /var/log/apache2/${USERERP}-access.log common
    RequestHeader set X-Forwarded-Proto "$PROTO"
    ProxyPass /.well-known/ !
    ProxyPass        /websocket ws://127.0.0.1:$WSPORT/websocket
    ProxyPassReverse /websocket ws://127.0.0.1:$WSPORT/websocket
    ProxyPass        / http://127.0.0.1:$HTTPPORT/
    ProxyPassReverse / http://127.0.0.1:$HTTPPORT/
EOF
}
apache_apply() {
  if (( DRY )); then echo "[dry] apachectl configtest && systemctl reload apache2"; return 0; fi
  if apachectl configtest 2>&1; then systemctl reload apache2
  else
    a2dissite "${USERERP}.conf" >/dev/null 2>&1 || true; rm -f "$VHOST"
    die "apache configtest failed: vhost removed, apache not reloaded"
  fi
}
{
  echo "<VirtualHost *:80>"
  echo "    ServerName $DOMAIN"
  echo "    DocumentRoot $WEBROOT"
  proxy_block
  echo "</VirtualHost>"
} | write_file "$VHOST" 644
run a2ensite "${USERERP}.conf"
apache_apply

if [[ "$WITH_SSL" == "Yes" ]]; then
  say "Let's Encrypt certificate"
  run "$CERTBOT_BIN" certonly -n --webroot -w "$WEBROOT" -d "$DOMAIN"
  {
    echo "<VirtualHost *:80>"
    echo "    ServerName $DOMAIN"
    echo "    DocumentRoot $WEBROOT"
    echo "    RewriteEngine On"
    echo '    RewriteCond %{REQUEST_URI} !^/.well-known/'
    echo "    RewriteRule ^/(.*)\$ https://$DOMAIN/\$1 [R=301,L]"
    echo "</VirtualHost>"
    echo "<VirtualHost *:443>"
    echo "    ServerName $DOMAIN"
    echo "    SSLEngine On"
    echo "    SSLCertificateFile    /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    echo "    SSLCertificateKeyFile /etc/letsencrypt/live/$DOMAIN/privkey.pem"
    proxy_block
    echo "</VirtualHost>"
  } | write_file "$VHOST" 644
  apache_apply
fi

say "Info file + aliases"
{
  echo "Odoo runbot: $REV"
  echo "Odoo branch: $ODOO_BRANCH ($ODOO_REPO)"
  echo "Custom modules: ${ADDONS_REPO:-none} ${ADDONS_BRANCH:+($ADDONS_BRANCH)}  ${EXTRA_DIR:+ + test-addons}"
  echo "Installed modules: $MODULES"
  echo "URL: $PROTO://$DOMAIN"
  echo "Odoo login: admin / password: $ADMIN_PASSWD"
  echo "Master password (DB manager): $MASTER_PASSWD"
  (( HAVE_PWMOD )) && { echo "Per-action passwords: drop=$DROP_PW  backup=$BKP_PW  restore=$RESTORE_PW"; }
  (( DBMGR )) && echo "DB manager: $PROTO://$DOMAIN/web/database/manager  (database names must start with: ${DBNAME})"
  echo "Ports: http=$HTTPPORT gevent(reserved)=$GEVENTPORT pg=${PGPORT_RB} ; PostgreSQL: $PG_MODE"
  echo "DB: $DBNAME"
  echo "Logs: $HOME_DIR/log/odoo.log   ($SCRIPT_DIR/LOG/$REV.log)"
} | write_file "$HOME_DIR/RB_info.txt" 600 "$USERERP:$USERERP"


{
  echo ""
  echo "# --- runbot $USERERP ---"
  [[ -n "$PGENV_HOST" ]] && echo "export PGHOST=$PGENV_HOST"
  echo "export PGPORT=$PGENV_PORT"
  echo "alias serverrestart='sudo systemctl restart $USERERP-server'"
  echo "alias serverstart='sudo systemctl start $USERERP-server'"
  echo "alias serverstop='sudo systemctl stop $USERERP-server'"
  echo "alias servertail='tail -f -n 100 ~/log/odoo.log'"
  echo "alias odoo-update='~/odoo.sh --stop-after-init -d $DBNAME -u'"
  echo "alias odoo-shell='~/odoo.sh shell -d $DBNAME'"
} | { if (( DRY )); then echo "[dry] would append to $HOME_DIR/.bashrc:"; sed 's/^/    | /'; else cat >> "$HOME_DIR/.bashrc"; chown "$USERERP:$USERERP" "$HOME_DIR/.bashrc"; fi; }

if (( DRY )); then echo; echo "######## End of dry run (nothing was modified) ########"
else
  echo; mask < "$HOME_DIR/RB_info.txt"; echo "(passwords: cat $HOME_DIR/RB_info.txt)"
  echo "Done. To update a module: su - $USERERP then 'serverstop; odoo-update my_module; serverstart'."
fi
