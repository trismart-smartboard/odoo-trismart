# from xmlrpc import client
import odoorpc

db_name = ''
username = ''
password = ''

sb_lead_id = ['001']

odoo = odoorpc.ODOO('localhost', port=8069)
odoo.login(db_name, username, password)

user_data = odoo.execute('smartboard.connector', 'create_project', sb_lead_id)
print(user_data)




