# from xmlrpc import client
import odoorpc

# db_name = 'demo1'
# username = 'admin'
# api_key = 'admin'
# server_url = ['localhost', 8069]

db_name = 'trismart-staging-15-0-3640780'
username = 'admin'
api_key = '0c5608e57939826227c64338c981070573de0700'
server_url = ['https://trismart-staging.odoo.com']

sb_lead_id = 14
project_template_id = 2
x_api_key = 'bWFnZ2llOnN1bW1lcnM'

odoo = odoorpc.ODOO(server_url[0], port=server_url[1])
odoo.login(db_name, username, api_key)

user_data = odoo.execute('smartboard.connector', 'create_project', sb_lead_id, x_api_key, project_template_id)
print(user_data)




