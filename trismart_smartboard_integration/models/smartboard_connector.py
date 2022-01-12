from odoo import api, fields, models, tools, SUPERUSER_ID

class SmartBoard(models.Model):
    _name = "smartboard.connector"
    _description = "SmartBoard Connector"

    @api.model
    def create_project(self, sb_lead_id, project_template_id):
        try:
            if sb_lead_id and project_template_id:
                partner_exist = self.env['res.partner'].search([('sb_lead_id', '=', sb_lead_id)], limit=1)
                lead_exist = self.env['crm.lead'].search([('sb_lead_id', '=', sb_lead_id)], limit=1)
                project_exist = self.env['project.project'].search([('sb_lead_id', '=', sb_lead_id)], limit=1)
                partner_id = []

                if not partner_exist:
                    # Create new partner
                    new_id = self.env['res.partner'].create({'name': 'SBLead-' + sb_lead_id, 'sb_lead_id': sb_lead_id, "sync_status" : '1'})
                    partner_id.append(new_id)

                if not lead_exist:
                    # Create new lead
                    lead_id = self.env['crm.lead'].create({'name': 'SBLead-' + sb_lead_id, 'sb_lead_id': sb_lead_id})
                    # Convert lead to opportunity
                    if partner_id:
                        customer = self.env['res.partner'].browse(partner_id[0])
                    else:
                        customer = self.env['res.partner'].browse(partner_exist)
                    vals = lead_id[0]._convert_opportunity_data(customer, team_id=False)
                    lead_id[0].write(vals)

                if not project_exist:
                    # Create new project
                    new_project = self.env['project.project'].search([('id', '=', project_template_id)]).create_project_from_template(sb_lead_id)
                    project = self.env['project.project'].search([('id', '=', new_project['res_id'])])
                    if partner_id:
                        project.partner_id = partner_id[0].id
                    else:
                        project.partner_id = partner_exist.id

                if not partner_exist:
                    return {"status": 200, "error": "partner created", "odoo_customer_id": partner_id[0].id}
            else:
                return {"status": 400, "error": "smartboard ID or template ID is null", "odoo_customer_id": None}
        except Exception as e:
            return {"status": 500,  "error": "Exception occurred. Detail: %s" % e, "odoo_customer_id": None}


