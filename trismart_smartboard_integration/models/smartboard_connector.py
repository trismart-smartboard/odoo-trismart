from odoo import api, fields, models, tools, SUPERUSER_ID

class SmartBoard(models.Model):
    _name = "smartboard.connector"
    _description = "SmartBoard Connector"

    def param_check(self, input_dict):
        valid = True
        error_dict = {}
        error = None
        if not input_dict['sb_lead_id']:
            error = "Smartboard ID is null"
        elif not input_dict['x_api_key']:
            error = "X API Key is null"
        elif type(input_dict['sb_lead_id']) is not int:
            error = "Smartboard ID is not an Integer"
        elif type(input_dict['x_api_key']) is not str:
            error = "X API Key is not a String"
        elif input_dict['project_template_id'] and type(input_dict['project_template_id']) is not int:
            error = 'Template ID is not an Integer'
        if error:
            valid = False
            error_dict = {"status": 400, "error": error, "odoo_customer_id": False}
        return [valid, error_dict]

    def create_non_template_project (self, sb_lead_id):
        project_env = self.env['project.project']
        default_template_id = int(self.env['ir.config_parameter'].sudo().get_param(
            'trismart_project_template_improvement.user_default_project_template')) or False
        if default_template_id:
            default_template = project_env.search([('id', '=', default_template_id)])
            project = default_template.create_project_from_template(sb_lead_id)
            project_new = project_env.search([('id', '=', project['res_id'])], limit=1)
        else:
            project_new = project_env.create({"name": 'SBLead-' + str(sb_lead_id), "sb_lead_id": sb_lead_id})
        return project_new

    @api.model
    def create_project(self, sb_lead_id, x_api_key, project_template_id=None):
        try:
            input_dict = {'sb_lead_id' : sb_lead_id, 'x_api_key' : x_api_key, 'project_template_id' : project_template_id}
            # Check input parameters:
            res = self.param_check(input_dict)
            if not res[0]:
                return res[1]

            partner_exist = self.env['res.partner'].search([('sb_lead_id', '=', sb_lead_id)], limit=1)
            lead_exist = self.env['crm.lead'].search([('sb_lead_id', '=', sb_lead_id)], limit=1)
            project_exist = self.env['project.project'].search([('sb_lead_id', '=', sb_lead_id)], limit=1)

            if not partner_exist:
                # Create new partner
                partner_new = self.env['res.partner'].create({'name': 'SBLead-' + str(sb_lead_id), 'sb_lead_id': sb_lead_id, 'x_api_key': x_api_key, "sync_status" : '1'})
            else:
                partner_exist.write({'x_api_key': x_api_key})
            partner_record = partner_exist if partner_exist else partner_new

            if not lead_exist:
                # Create new lead
                lead_new = self.env['crm.lead'].create({'name': 'SBLead-' + str(sb_lead_id), 'sb_lead_id': sb_lead_id})
                # Convert lead to opportunity
                vals = lead_new._convert_opportunity_data(partner_record, team_id=False)
                lead_new.write(vals)

            if not project_exist:
                project_env = self.env['project.project']
                # Create new project
                if project_template_id:
                    template = project_env.search([('id', '=', project_template_id), ('is_template', '=', True)])
                    if template:  # Template exists
                        project = template.create_project_from_template(sb_lead_id)
                        project_new = project_env.search([('id', '=', project['res_id'])], limit=1)
                    else:
                        project_new = self.create_non_template_project(sb_lead_id)
                else:
                    project_new = self.create_non_template_project(sb_lead_id)
                # Add partner_id
                project_new.partner_id = partner_record.id

            if partner_exist:
                return {"status": 200, "error": "", "odoo_customer_id": partner_exist.id}
            else:
                return {"status": 200, "error": "", "odoo_customer_id": partner_new.id}
        except Exception as e:
            return {"status": 500,  "error": "Exception occurred. Detail: %s" % e, "odoo_customer_id": False}


