#!/usr/bin/env python

import yaml
import sys
import os
import ast
import json

yaml_env_file = str(sys.argv[1])
path_project_name = "/var/lib/odoo/upgrade_module/check_point.txt"

odoo_upgrade = """
#!/bin/bash
#Create Config dir
mkdir -p /etc/odoo
#Generate Odoo config file
python3 /make_env.py
#Run Odoo Upgrade, Install
"""

try: 
	version_list = open(path_project_name, "r")
	old_version = version_list.read()
	version_list.close()
except:
	old_version = ""
if old_version != "":
	list_old_version = ast.literal_eval(old_version)
else:
	list_old_version = []

def get_version_yml():
    with open(yaml_env_file, 'r') as stream:
        try:
        	data_yaml = yaml.safe_load(stream)
        	key_arr = [k for k,v in data_yaml.items()]
        	dict_arr = [{k: v} for k,v in data_yaml.items()]
        	if old_version == "":
        		print ("The first deploy, Update code version list to checkpoint!!!")
        		file = open(path_project_name, "w")
        		file.write(repr(key_arr))
        		file.close()
        		d = dict();
        		d['check_version'] = key_arr
        		d['result'] = dict_arr        		
        		return d
        	else: 
        		check_version = list(set(key_arr) - set(list_old_version))        		
        		if len(check_version) == 0:
        			print ("Do not have any update!!!")
        		else:
        			s = []      			
        			print('The new version: %s' % check_version)
        			file = open(path_project_name, "w")
        			file.write(repr(key_arr))
        			file.close()        			
        			for i in check_version:
        				check_version_1 = key_arr.index(i)
        				result = dict_arr[check_version_1]
        				s.append(result)   			
        			d = dict();
        			d['check_version'] = check_version
        			d['result'] = s      	       
        			return d
        	        
        except yaml.YAMLError as exc:
            print(exc)
def upgrade_module_list(check_version, result):
	module_list_upgrade = set()
	module_list_install = set()
	db = set()
	for version in check_version:
		index = check_version.index(version)
		##Get module list upgrade!!!
		module_list_need_upgrade = result[index][version]['upgrade_modules']
		if module_list_need_upgrade is None:
			module_list_upgrade.update([module_list_need_upgrade])
		else:
			module_list_upgrade.update(module_list_need_upgrade)
		##Get db list!!!
		db_list = result[index][version]['database']
		if db_list is None:
			db.update([db_list])
		else:
			db.update(db_list)
		##Get module list install!!!
		module_list_need_install = result[index][version]['install_modules']
		if module_list_need_install is None:	
			module_list_install.update([module_list_need_install])
		else:
			module_list_install.update(module_list_need_install)		
	
	module_list_upgrade_final = ','.join(list(filter(None, module_list_upgrade)))
	module_list_install_final = ','.join(list(filter(None, module_list_install)))	
	db_list_final = ' '.join((filter(None, db)))

	if len(db_list_final) == 0:
		if len(module_list_upgrade_final) != 0 and len(module_list_install_final) != 0:
			print ("Running Upgrade Modules: %s" % module_list_upgrade_final)
			print ("Running Install Modules: %s" % module_list_install_final)
			print ("Database: %s" % db_list_final)		
			file = open("./odoo_upgrade.sh", "w")
			file.write(odoo_upgrade + "/opt/odoo/odoo/odoo-bin --config /etc/odoo/odoo.conf --stop-after-init -i %s -u %s" % (module_list_install_final, module_list_upgrade_final))
			file.close()
	
		elif len(module_list_upgrade_final) != 0:
			print ("Running Upgrade Modules: %s" % module_list_upgrade_final)
			print ("Database: %s" % db_list_final)		
			file = open("./odoo_upgrade.sh", "w")
			file.write(odoo_upgrade + "/opt/odoo/odoo/odoo-bin --config /etc/odoo/odoo.conf --stop-after-init -u %s" % (module_list_upgrade_final))
			file.close()
			
		elif len(module_list_install_final) != 0:
			print ("Running Install Modules: %s" % module_list_install_final)
			print ("Database: %s" % db_list_final)		
			file = open("./odoo_upgrade.sh", "w")
			file.write(odoo_upgrade + "/opt/odoo/odoo/odoo-bin --config /etc/odoo/odoo.conf --stop-after-init -i %s" % (module_list_install_final))
			file.close()
		else:
			print ("Do not have anythings upgrade")
			file = open("./odoo_upgrade.sh", "w")
			file.write("#!/bin/bash" + "\n" + "echo 'Do not have anythings upgrade'")
			file.close()
	elif len(db_list_final) != 0:
		if len(module_list_upgrade_final) != 0 and len(module_list_install_final) != 0:
			print ("Running Upgrade Modules: %s" % module_list_upgrade_final)
			print ("Running Install Modules: %s" % module_list_install_final)
			print ("Database: %s" % db_list_final)		
			file = open("./odoo_upgrade.sh", "w")
			file.write(odoo_upgrade + "db_list=\"%s\"" % (db_list_final) + "\n" + "for db in $db_list;do" + "\n" + "\t" + "/opt/odoo/odoo/odoo-bin --config /etc/odoo/odoo.conf --stop-after-init -i %s -u %s -d $db" % (module_list_install_final, module_list_upgrade_final) + "\n" + "done")
			file.close()
	
		elif len(module_list_upgrade_final) != 0:
			print ("Running Upgrade Modules: %s" % module_list_upgrade_final)
			print ("Database: %s" % db_list_final)		
			file = open("./odoo_upgrade.sh", "w")
			file.write(odoo_upgrade + "db_list=\"%s\"" % (db_list_final) + "\n" + "for db in $db_list;do" + "\n" + "\t" + "/opt/odoo/odoo/odoo-bin --config /etc/odoo/odoo.conf --stop-after-init -u %s -d $db" % (module_list_upgrade_final) + "\n" + "done")
			file.close()
			
		elif len(module_list_install_final) != 0:
			print ("Running Install Modules: %s" % module_list_install_final)
			print ("Database: %s" % db_list_final)		
			file = open("./odoo_upgrade.sh", "w")
			file.write(odoo_upgrade + "db_list=\"%s\"" % (db_list_final) + "\n" + "for db in $db_list;do" + "\n" + "\t" + "/opt/odoo/odoo/odoo-bin --config /etc/odoo/odoo.conf --stop-after-init -i %s -d $db" % (module_list_install_final) + "\n" + "done")
			file.close()
		else:
			print ("Do not have anythings upgrade")
			file = open("./odoo_upgrade.sh", "w")
			file.write("#!/bin/bash" + "\n" + "echo 'Do not have anythings upgrade'")
			file.close()

if __name__ == "__main__":
	version_list_deploy = get_version_yml()
	if version_list_deploy is None:	
		file = open("./odoo_upgrade.sh", "w")
		file.write("#!/bin/bash" + "\n" + "echo 'Do not have anythings upgrade'")
		file.close()
	else:
		upgrade_module_list(version_list_deploy['check_version'], version_list_deploy['result'])