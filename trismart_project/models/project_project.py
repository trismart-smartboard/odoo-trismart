from odoo import models, fields, api, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    sb_lead_id = fields.Integer(string='Smartboard Lead ID')
    # Energy Usage Fields
    utility = fields.Char('Utility Company')
    utility_account_number = fields.Char('Utility Account Number')
    authority_having_jurisdiction = fields.Char('AHJ')
    billing_period_one_start_date = fields.Date('Billing Period Start Date')

    # Monthly Usage Fields
    monthly_usage_ids = fields.One2many('monthly.usage', 'project_id', string='Monthly Usage')

    # Metrics Final Fields
    proposal_id = fields.Char('Proposal Id')
    usage_collected = fields.Boolean('Utility Bill Collected (Y/N)')
    hoa_name = fields.Char('HOA Name')
    hoa_phone_email = fields.Char('HOA Email/Phone')
    module_make = fields.Char('Module Make')
    module_model = fields.Char('Module Model')
    module_size = fields.Integer('Module Size')
    inverter_make = fields.Char('Inverter Make')
    inverter_model = fields.Char('Inverter Model')
    optimizer_make = fields.Char('Optimizer Manufacturer')
    optimizer_model = fields.Char('Optimizer Model')
    usage_offset = fields.Float('Usage Offset')
    total_cost = fields.Float('Total Cost')
    lease_price_per_kwh = fields.Float('Lease Price per Watt')
    lease_escalator = fields.Float('Lease Escalator')
    lender = fields.Char('Lender')
    finance_term = fields.Integer('Finance Term in Years')
    finance_apr = fields.Float('Finance APR')
    down_payment = fields.Float('Down Payment')

    # Module Array, Adders and Incentive
    module_array_ids = fields.One2many('project.module.array', 'project_id', string='Monthly Array')
    adder_ids = fields.One2many('project.adder', 'project_id', string='Adder')
    incentive_ids = fields.One2many('project.incentive', 'project_id', string='Incentive')
    document_ids = fields.One2many('documents.document', 'project_id', string='Documents for Project')
