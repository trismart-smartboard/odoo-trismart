# from xmlrpc import client
import odoorpc
# server_url = 'http://localhost:8069'
db_name = 'demo1'
username = 'admin'
password = 'admin'

sb_lead_id = '001'
project_template_id = 2

odoo = odoorpc.ODOO('localhost', port=8069)
odoo.login(db_name, username, password)

user_data = odoo.execute('smartboard.connector', 'create_project', sb_lead_id, project_template_id)
print(user_data)




