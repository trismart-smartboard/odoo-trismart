import json
import requests
import base64


class Extractor:
    """
    Helper to extract data from SmartBoard Response
    """
    models_to_extract = ['crm.lead', 'project.project', 'res.partner']
    mapped_field_table = {
        'id': 'sb_lead_id',
        'cell_phone': 'phone',
        'home_phone': 'mobile',
        'address': 'street',
        'address_line_2': 'street2',
        'state': 'state_id',
        'lead_source': 'source_id',
        'image_name': 'name',
        'document_name': 'name',
        'title': 'image_subtype',
        'image_url': 'datas',
        'document_url': 'datas',
        'thumbnail_image_url': 'thumbnail'
    }
    excluded_fields = ['document_type_id']

    def extract_response_json(self, data):
        content = data.content
        if isinstance(content, bytes):
            decoded_data = data.content.decode('utf-8')
            index_to_get = decoded_data.find('\"Lead\":')
            content = '{' + decoded_data[index_to_get:]
        return json.loads(content)

    @staticmethod
    def extract_monthly_usage(value):
        """
        Extract Monthly Usage from Response to List of Dictionary
        [
        {month: ...., 'usage_type': ...., 'usage_number': ....},
        {month: ...., 'usage_type': ...., 'usage_number': ....},
        {month: ...., 'usage_type': ...., 'usage_number': ....}
        ]
        :param value:
        :return:
        """
        monthly_usage_ids = []
        for usage, number in value.items():
            if 'annual_consumption' in usage:
                continue
            if 'billing' in usage:
                month = usage.split('_')[0]
                billing = {'month': month, 'usage_type': 'billing', 'usage_number': number}
                monthly_usage_ids.append(billing)
            elif 'consumption' in usage:
                month = usage.split('_')[0]
                consumption = {'month': month, 'usage_type': 'consumption', 'usage_number': number}
                monthly_usage_ids.append(consumption)
        return monthly_usage_ids

    def extract_lead_image_data(self, data):
        document_datas = []
        for document in data:
            document_data = {}
            for key, value in document.items():
                if key in self.mapped_field_table:
                    key = self.mapped_field_table[key]
                if key in ['datas', 'thumbnail']:
                    # TODO: Handle api error with image
                    if not value:
                        continue
                    response = requests.get(value)
                    value = base64.encodebytes(response.content)
                document_data.update({'folder_id': 'Project/Images'})
                document_data.update({key: value})
            document_datas.append(document_data)
        return document_datas

    def extract_document_data(self, data):
        document_datas = []
        for document_tab, list_documents in data.items():
            for d in list_documents:
                document_data = {'document_subtype': document_tab, 'folder_id': 'Project/Documents'}
                for key, value in d.items():
                    if key in self.mapped_field_table:
                        key = self.mapped_field_table[key]
                    if key in ['datas', 'thumbnail']:
                        # TODO: Handle api error with image
                        if not value:
                            continue
                        response = requests.get(value)
                        value = base64.encodebytes(response.content)
                    if key in self.excluded_fields:
                        continue
                    document_data.update({key: value})
                document_datas.append(document_data)
        return document_datas

    def extract_data(self, data_object):
        """
        Extract response from SmartBoard for each type of object
        :param data_object: ['lead', 'project', 'customer']
        :return:
        """
        extracted_data = {}
        for model in self.models_to_extract:
            dashed_model = model.replace('.', '_')
            method_extract = f"_extract_{dashed_model}_data"
            if hasattr(self, method_extract):
                extracted_data[model] = getattr(self, method_extract)(data_object)
        return extracted_data

    def _extract_crm_lead_data(self, data_object):
        """
        Extract Dictionary Lead Data from SmartBoard Response
        :param data_object:
        :return:
        """
        lead_data = {}
        for key, value in data_object.items():
            if key in ['Lead', 'Association']:
                new_value = {}
                for smartboard_key in value:
                    odoo_key = self.mapped_field_table.get(smartboard_key, smartboard_key)
                    new_value[odoo_key] = value[smartboard_key]
                lead_data.update(new_value)
        return lead_data

    def _extract_project_project_data(self, data_object):
        """
        Extract data_object Dictionary Data from SmartBoard Response
        :param data_object:
        :return:
        """
        project_data = {}
        for key, value in data_object.items():
            if key in ['EnergyUsage', 'MetricsFinal']:
                project_data.update(value)
            if key == 'MonthlyUsage':
                monthly_usage_ids = self.extract_monthly_usage(value)
                project_data.update({'monthly_usage_ids': monthly_usage_ids})
            if key == 'LeadImage':
                document_ids = self.extract_lead_image_data(value)
                if project_data.get('document_ids', False):
                    project_data['document_ids'] += document_ids
                else:
                    project_data.update({'document_ids': document_ids})
            if key == 'Document':
                document_ids = self.extract_document_data(value)
                if project_data.get('document_ids'):
                    project_data['document_ids'] += document_ids
                else:
                    project_data.update({'document_ids': document_ids})
            if key == 'ModuleArray':
                continue
                # project_data.update({'module_array_ids': value})
            if key == 'Adder':
                continue
                # project_data.update({'adder_ids': value})
            if key == 'Incentive':
                continue
                # project_data.update({'incentive_ids': value})

        return project_data

    def _extract_res_partner_data(self, data_object):
        """
        Extract Dictionary Res.Partner Data from SmartBoard Dictionary
        :param data_object:
        :return:
        """
        customer_data = {}
        customer_object = data_object['Customer']
        for key, value in customer_object.items():
            if key in self.mapped_field_table:
                key = self.mapped_field_table[key]
            customer_data.update({key: value})

        return customer_data
