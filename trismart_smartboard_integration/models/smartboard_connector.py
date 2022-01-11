from odoo import api, fields, models, tools, SUPERUSER_ID

class SmartBoard(models.Model):
    _name = "smartboard.connector"
    _description = "Create SB Project"

    @api.model
    def create_project(self, sb_lead_id):
        try:
            if len(sb_lead_id):
                partner_exist = self.env['res.partner'].search([('sb_lead_id', '=', sb_lead_id[0])], limit=1)
                lead_exist = self.env['crm.lead'].search([('sb_lead_id', '=', sb_lead_id[0])], limit=1)
                project_exist = self.env['project.project'].search([('sb_lead_id', '=', sb_lead_id[0])], limit=1)

                if not partner_exist:
                    # Create new partner
                    partner_id = self.env['res.partner'].create({'name': 'SBLead-' + sb_lead_id[0], 'sb_lead_id': sb_lead_id[0], "sync_status" : '1'})
                if not lead_exist:
                    # Create new lead
                    lead_id = self.env['crm.lead'].create({'name': 'SBLead-' + sb_lead_id[0], 'sb_lead_id': sb_lead_id[0]})

                    # Convert lead to opportunity
                    customer = self.env['res.partner'].browse(partner_id) if partner_id else partner_exist
                    for lead in lead_id:
                        vals = lead._convert_opportunity_data(customer, team_id=False)
                        lead.write(vals)

                if not project_exist:
                    # Create new project
                    project_id = self.env['project.project'].create({'name': 'SBLead-' + sb_lead_id[0], 'sb_lead_id': sb_lead_id[0]})
                    project_id.partner_id = partner_id

                if partner_exist:
                    return {"status": 200,  "message": "partner exists", "odoo_customer_id": []}
                else:
                    return {"status": 200, "message": "partner created", "odoo_customer_id": partner_id.id}
            else:
                return {"status": 400, "message": "smartboard ID is null", "odoo_customer_id": None}
        except Exception as e:
            return {"status": 500,  "message": "Exception occurred. Detail: %s" % e, "odoo_customer_id": None}


