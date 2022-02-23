# from xmlrpc import client
import odoorpc

db_name = 'Odoo'
username = 'admin'
api_key = 'admin'
server_url = ['localhost', 8071]

sb_lead_id = 5196644
x_api_key = '281a27b3f1865a80f6d0acd5fb307cbf'
project_template_id = 45

odoo = odoorpc.ODOO(server_url[0], port=server_url[1])
# odoo = odoorpc.ODOO(server_url)
odoo.login(db_name, username, api_key)

user_data = odoo.execute('smartboard.connector', 'create_project', sb_lead_id, x_api_key, project_template_id)
# user_data = odoo.execute('smartboard.connector', 'create_project', sb_lead_id, x_api_key)
print(user_data)
