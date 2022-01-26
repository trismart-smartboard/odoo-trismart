from odoo import models, fields, api, _, Command


class SmartBoardProcessor(models.TransientModel):
    _name = 'smartboard.processor'
    _description = 'SmartBoard Processor'

    def process_data(self, response_data):
        """
        Prepare response data from SmartBoard to data ready to be saved in Odoo
        :param response_data:
        :return: {lead: lead_data, project: project_data, customer: customer_data}
        """
        lead_response_data = response_data['Lead']
        customer_response_data = response_data['Customer']
        project_keys = ['MonthlyUsage', 'MetricsFinal', 'ModuleArray']
        project_response_data = {}
        for key in project_keys:
            project_response_data.update({key: response_data[key]})
        lead_data = self.process_lead_data(lead_response_data)
        customer_data = self.process_customer_data(customer_response_data)
        project_data = self.process_project_data(project_response_data)
        return lead_data, customer_data, project_data

    def process_lead_data(self, lead_response_data):
        """
        Prepare lead_data from lead_response_data tp data ready to be saved in Odoo
        :param lead_response_data:
        :return: lead_data
        """
        ready_data = {}
        for key, value in lead_response_data.items():
            if key == 'created':
                ready_data[key] = fields.Datetime.from_string(value)
            if key == 'lead_source':
                source = self.env['utm.source'].search([('sb_id', '=', value['id'])])
                if not source:
                    source = self.env['utm.source'].create({'sb_id': value['id'], 'name': value['name']})
                ready_data['source_id'] = source.id
            elif key == 'account_id':
                account = self.env['res.partner'].search([('sb_id', '=', value['id'])])
                if not source:
                    account = self.env['res.partner'].create({'sb_id': value['id'], 'name': value['name']})
                ready_data['account_id'] = account.id
            else:
                ready_data[key] = value
        return ready_data

    def process_project_data(self, project_response_data):
        """
        Prepare project_data from lead_response_data tp data ready to be saved in Odoo
        :param project_response_data:
        :return: project_data
        """
        ready_data = {}
        monthly_usages = project_response_data['MonthlyUsage']
        monthly_usage_env = self.env['monthly.usage']
        monthly_usage_ids = []
        for usage, number in monthly_usages.items():
            if 'billing' in usage:
                month = usage.split('_')[0]
                billing = monthly_usage_env.create({'month': month, 'usage_type': 'billing', 'usage_number': number})
                monthly_usage_ids.append(Command.link(billing.id))
            elif 'consumption' in usage:
                month = usage.split('_')[0]
                consumption = monthly_usage_env.create(
                    {'month': month, 'usage_type': 'consumption', 'usage_number': number})
                monthly_usage_ids.append(Command.link(consumption.id))
        ready_data.update({'monthly_usages': monthly_usage_ids})
        metric_final = project_response_data['MetricsFinal']
        for key, value in metric_final.items():
            ready_data.update({key: value})
        module_array = project_response_data['ModuleArray']
        module_array_ids = []
        for array in module_array:
            new_module_array = self.env['project.module.array'].create(array)
            module_array_ids.append(Command.link(new_module_array.id))
        ready_data.update({'module_array_ids': module_array_ids})
        return ready_data

    def process_customer_data(self, customer_response_data):
        """
        Prepare project_data from lead_response_data tp data ready to be saved in Odoo
        :param customer_response_data:
        :return: customer_data
        """
        ready_data = {}
        for key, value in customer_response_data.items():
            if key == 'cell_phone':
                ready_data.update({'phone': value})
            elif key == 'home_phone':
                ready_data.update({'mobile': value})
            elif key == 'address':
                ready_data.update({'street': value})
            elif key == 'address_line_2':
                ready_data.update({'street2': value})
            elif key == 'state':
                state = self.env['res.country.state'].search([('name', '=', value.lower())])
                ready_data.update({'state_id': state.id})
            else:
                ready_data.update({key: value})
        return ready_data
