#!/bin/bash
#Create Config dir
mkdir -p /etc/odoo
#Generate Odoo config file
python3 /make_env.py
#Run rsyslog
rsyslogd -n -f /etc/rsyslog.conf &
#Run Odoo
/opt/odoo/odoo/odoo-bin --config /etc/odoo/odoo.conf --syslog
