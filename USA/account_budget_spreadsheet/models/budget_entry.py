import xlsxwriter
import io
from odoo import models, api, _, fields


class BudgetEntry(models.AbstractModel):
    """
    An inherit model of account report to implement get_xlsx method to print excel
    """
    _inherit = 'account.report'
    _name = 'usa.budget.entry'
    _description = 'Budget Entry'

    def get_xlsx(self, options):
        """
        Print Excel Format from an event call from client
        :param options:
        :return:
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Sheet 1')
        # Styles
        default_style = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'align': 'left'})
        header_style = workbook.add_format({'font_name': 'Arial', 'font_size': 10, 'bold': True})
        default_style.set_locked(False)
        default_style.set_num_format('#,##0.00')
        header_style.set_num_format('#,##0.00')
        # Set the first column width to 50
        sheet.set_column(1, 1, 50)
        sheet.set_column(2, 50, 15)
        data = options.get('data', [])
        row = 1
        # Iterate over the data and write it out row by row.
        for row_dict in data:
            col = 1
            row_index = data.index(row_dict)
            row_data = row_dict['data']
            if row_index >= 4:
                row_data = ['{:.2f}%'.format(row_data[i]*100) if i > 1 and i % 4 == 0 else row_data[i] for i in
                            range(len(row_data))]
                sheet.write_row(row, col, row_data, default_style)
            else:
                sheet.write_row(row, col, row_data, header_style)
            row += 1

        sheet.set_column('A:A', None, None, {'hidden': 1})  # hide ID column
        sheet.protect()

        workbook.close()
        output.seek(0)
        generated_file = output.read()
        output.close()

        return generated_file
