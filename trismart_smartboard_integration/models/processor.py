from odoo import models, fields, api, _, Command


class SmartBoardProcessor(models.TransientModel):
    _name = 'smartboard.processor'
    _description = 'SmartBoard Processor'

    def parse_data(self, model, data):
        """
        :param model:
        :param data:
        :return:
        """
        ready_values = {}
        model = self.env['ir.model'].search([('model', '=', model)])
        for field_name, value in data.items():
            parsed_value = value
            field = self.env['ir.model.fields'].search([('model_id', '=', model.id), ('name', '=', field_name)])
            field_type = field.ttype
            if not field_type:
                continue
            parse_method = f"parse_{field_type}_data"
            if hasattr(self, parse_method):
                parsed_value = getattr(self, parse_method)(value, field)
            ready_values.update({field_name: parsed_value})
        return ready_values

    def parse_datetime_data(self, value, field=None):
        """

        :param value:
        :param field:
        :return:
        """
        return fields.Datetime.from_string(value)

    def get_field_search(self, related_model):
        field_search_dict = {
            'res.country.state': 'code',
            'documents.folder': 'name',
            'documents.subtype': 'name'
        }
        return field_search_dict[related_model]

    def parse_many2one_data(self, value, field):
        """

        :param value:
        :param field:
        :return:
        """
        related_model = field.relation
        if isinstance(value, str):
            field_search = self.get_field_search(related_model)
            vals = {field_search: value}
            record = self.env[related_model].search([(field_search, '=', value)])
        elif isinstance(value, dict):
            if value.get('id', False):
                vals = {'sb_id': int(value['id'])}
                record = self.env[related_model].search([('sb_id', '=', int(value['id']))])
            else:
                return
        if not record:
            record = self.env[related_model].create(vals)
        return record.id

    def parse_one2many_data(self, value, field):
        """

        :param value:
        :param field:
        :return:
        """
        related_model = self.env['ir.model'].search([('model', '=', field.relation)])
        records = []
        for val in value:
            for field_name, field_value in val.items():
                parsed_value = None
                _field = self.env['ir.model.fields'].search(
                    [('model_id', '=', related_model.id), ('name', '=', field_name)])
                field_type = _field.ttype
                if not field_type:
                    continue
                parse_method = f"parse_{field_type}_data"
                if hasattr(self, parse_method):
                    parsed_value = getattr(self, parse_method)(field_value, _field)
                val.update({field_name: parsed_value or field_value})
                # ready_values.update({field_name: parsed_value})
                # # TODO: Less hard code
                #
                # if k == 'image_subtype':
                #     subtype = self.env['documents.subtype'].search([('name', '=', v)])
                #     val.update({k: (subtype and subtype.id) or False})
                # if k == 'folder_id':
                #     folder = self.env['documents.folder'].search([('name', '=', v)])
                #     val.update({k: (folder and folder.id) or False})
                # if k == 'created':
                #     val.update({k: self.parse_datetime_data(v)})
            new_record = self.env[field.relation].create(val)
            records.append(Command.link(new_record.id))
        return records

    def parse_float_data(self, value, field):
        return (value and float(value)) or 0.0

    def parse_integer_data(self, value, field):
        return (value and int(value)) or 0
