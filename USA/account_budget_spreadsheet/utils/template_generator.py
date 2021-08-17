from odoo import modules
import re
import json
import uuid
from .predefined_columns import col_name, col_actual, col_budget, col_variance, col_perf, COLUMNS, header_format, \
    POSITIVE_FILL_COLOR, POSITIVE_TEXT_COLOR, NEGATIVE_FILL_COLOR, NEGATIVE_TEXT_COLOR
from .pivots_template import pivot_template

QUARTER_IDX = [3, 7, 11, 15]
BEGIN_FISCAL_YEAR = 2020
TIME = {
    "month": 12,
    "quarter": 4
}
TIME_DICT = {
    "quarter_in_month": {3: "Quarter 1", 7: "Quarter 2", 11: "Quarter 3", 15: "Quarter 4"},
    "quarter": {0: "Quarter 1", 1: "Quarter 2", 2: "Quarter 3", 3: "Quarter 4"},
    "month": {0: "January", 1: "February", 2: "March", 4: "April", 5: "May", 6: "June", 8: "July", 9: "August",
              10: "September", 12: "October", 13: "November", 14: "December"},
}
INDEX_TO_MONTH = {
    "month": {0: 1,
              1: 2,
              2: 3,
              3: "Quarter 1",
              4: 4,
              5: 5,
              6: 6,
              7: "Quarter 2",
              8: 7,
              9: 8,
              10: 9,
              11: "Quarter 3",
              12: 10,
              13: 11,
              14: 12,
              15: "Quarter 4",
              16: "Year"},
    "quarter": {
        0: 1,
        1: 2,
        2: 3,
        3: 4,
        4: "Year"
    }
}
# Beginning cell number not including title
start = 5
# Dictionary which defined content in each cells in sheet
# cells = {"A3": ... , "A4": ...., "M5": ...}

NUMBER_COLUMN_PER_PERIOD = 4


def build_content(i, period_type, year):
    """
    This function returns name for each period in a year based on the index
    For example: Monthly report
    i       0        | 1        | 2        | 3        | 4        | 5        | 6        | 7        |
    ------------------------------------------
    Name   January   | February | March    | Quarter 1| April   | May      | June      | Quarter 2 |
    :param i:
    :param period_type:
    :param year:
    :return:
    """
    if i in QUARTER_IDX and period_type == 'month':
        content = f"{TIME_DICT['quarter_in_month'][i]} - {year}"
    elif i == 4 and period_type == 'quarter' or i == 16 and period_type == 'month':
        content = f"Year {year}"
    else:
        content = f"{TIME_DICT[period_type][i]} - {year}"
    return content


def build_condition_format(lines_dict, period_type, green_on_positive):
    ranges = []
    periods = TIME[period_type]
    modified_periods = periods + 5 if period_type == 'month' else periods + 1
    name_variance = [COLUMNS[3 + NUMBER_COLUMN_PER_PERIOD * i] for i in range(modified_periods)]
    for letter in name_variance:
        for i in range(len(lines_dict) - 1):
            if lines_dict[i]['green_on_positive'] == green_on_positive:
                if lines_dict[i + 1]['green_on_positive'] == green_on_positive:
                    ranges.append(f"{letter}{lines_dict[i]['cell']}:{letter}{lines_dict[i + 1]['cell']}")
                else:
                    ranges.append(f"{letter}{lines_dict[i]['cell']}:{letter}{lines_dict[i + 1]['cell'] - 1}")
    rule_positive = {"id": str(uuid.uuid4()),
                     "rule": {
                         "type": "CellIsRule",
                         "operator": "GreaterThan",
                         "values": [
                             "0",
                             ""
                         ],
                         "stopIfTrue": False,
                         "style": {
                             "bold": True,
                             "fillColor": POSITIVE_FILL_COLOR if green_on_positive else NEGATIVE_FILL_COLOR,
                             "textColor": POSITIVE_TEXT_COLOR if green_on_positive else NEGATIVE_TEXT_COLOR
                         }
                     },
                     "ranges": ranges
                     }
    rule_negative = {"id": str(uuid.uuid4()),
                     "rule": {
                         "type": "CellIsRule",
                         "operator": "LessThan",
                         "values": [
                             "0",
                             ""
                         ],
                         "stopIfTrue": False,
                         "style": {
                             "bold": True,
                             "fillColor": NEGATIVE_FILL_COLOR if green_on_positive else POSITIVE_FILL_COLOR,
                             "textColor": NEGATIVE_TEXT_COLOR if green_on_positive else POSITIVE_TEXT_COLOR
                         }
                     },
                     "ranges": ranges
                     }
    return [rule_positive, rule_negative]


def generate_formula_balance_sheet(formula, period, year, pivot_id, i, max_time, sign):
    time_range = range(1, 13) if period['type'] == 'month' else range(1, 5)
    for previous_year in range(BEGIN_FISCAL_YEAR, year + 1):
        for previous_time in time_range:
            if previous_time >= max_time and previous_year == year:
                break
            previous_period_time = f"0{previous_time}" if period['type'] == 'month' and previous_time <= 9 \
                else previous_time
            formula += f"+ (-PIVOT(\"{pivot_id}\",\"balance\",\"account_id\",PIVOT.POSITION(\"{pivot_id}\"," \
                       f"\"account_id\",{i + 1}),\"date:{period['type']}\",\"{previous_period_time}/{previous_year}\")" \
                       f"*{sign})"
    return formula


def generate_formula_aggregation(time, col, idx, period_type):
    """
    This function will generate formula for quarter columns and year columns based on formula of months, quarters
    ACTUAL (Q1) = ACTUAL (JANUARY) + ACTUAL (FEBRUARY) + ACTUAL (MARCH)
                = B4 + C4 + D4
    ACTUAL (YEAR) = ACTUAL (Q1) + ACTUAL (Q2) + ACTUAL (Q3) + ACTUAL (Q4)
                 = E8 + H8 + ....
    BUDGET (Q1) = BUDGET (JANUARY) + BUDGET (FEBRUARY) + BUDGET (MARCH)
    BUDGET (YEAR) = BUDGET (Q1) + BUDGET (Q2) + BUDGET (Q3) + BUDGET (Q4)
    :param time:
    :param col:
    :param idx:
    :param period_type:
    :return:
    """
    col_idx = COLUMNS.index(col)
    if "Quarter" in time:
        cols_name = [COLUMNS[col_idx - NUMBER_COLUMN_PER_PERIOD * j] for j in range(1, 4)]
    else:
        if period_type == "month":
            cols_name = [COLUMNS[col_idx - 4 - 4 * NUMBER_COLUMN_PER_PERIOD * j] for j in range(0, 4)]
        else:
            cols_name = [COLUMNS[col_idx - 4 - NUMBER_COLUMN_PER_PERIOD * j] for j in range(0, 4)]

    formula = "="
    for month in cols_name:
        formula += f"+ {month}{idx}"
    return formula


def generate_formula_from_code_to_cell(name, col, lines):
    """
    This function will calculate NUMBER of cell based on FORMULA of LINE
    For example:
    Operating Income : B7
    Cost of revenue: B9
    Then this function will calculate Gross Profit cell number = B7 - B9 and store in 'domain'
    :param name:
    :param col:
    :param lines:
    :return:
    """
    if name == 'perf':
        cells = [line['cell'] for line in lines]
        col1_idx, col2_idx = COLUMNS.index(col) - 3, COLUMNS.index(col) - 2
        col1, col2 = COLUMNS[col1_idx], COLUMNS[col2_idx]
        domains = [f"=iferror({col1}{cell}/{col2}{cell},0)" for cell in cells]
    else:
        domains = [line["domain"] for line in lines]
        for _ in range(len(domains)):
            d = domains[_]
            if type(d[0]) is str:
                new_domain = "="
                ops_list = re.split('(\W+)', d[0])
                for i in range(len(ops_list)):
                    if i % 2 == 0:
                        code = ops_list[i]
                        cell_number = list(filter(lambda x: x['code'] == code, lines))
                        if len(cell_number) == 0:
                            new_domain += "0"
                        else:
                            new_domain += (col + str(cell_number[0]['cell']))
                    else:
                        cell_number = ops_list[i]
                        new_domain += cell_number
                domains[_] = new_domain
    return domains


def generate_pivots(lines_dict, period_type, analytic_account=None):
    pivots = {}
    pivots_in_sheet = []
    for i in range(len(lines_dict)):
        lines_dict[i]['pivot_id'] = i
        if not lines_dict[i]['is_lowest']:
            continue
        pivots_in_sheet.append(i)
        pivots[i] = pivot_template.copy()
        domain = pivots[i]['domain']
        analytic_account_domain = [[
            "analytic_account_id",
            "=",
            analytic_account.id
        ]] if analytic_account else []
        pivots[i]['colGroupBys'] = [f"date:{period_type}"]
        pivots[i]['domain'] = domain + lines_dict[i]['domain'] + analytic_account_domain
        pivots[i]['context']["pivot_column_groupby"] = [f"date:{period_type}"]
        pivots[i]['id'] = i

    return pivots, pivots_in_sheet


def generate_columns(sheet, period_type, name, pivots_in_sheet, year, analytic_account, currency):
    """
    This function will define cells number based on Parameter that we want to show
    For Example: Actuals, Budget , Variance, Perf -> B4,F4...: Actual, C4,G4..: Budget, D4,H4...: Variance,...
    :param period_type:
    :param name:
    :param pivots_in_sheet:
    :param year:
    :return:
    sheet = {
    colA: {A1:,A2:},
    colB: {B1:,B2:},...
    }
    """
    sheet['colA'] = col_name.copy()
    sheet['colA']['A1']['content'] = name
    sheet['colA']['A2']['content'] = "Analytic Account: " + analytic_account.name + " - " if analytic_account else ""
    sheet['colA']['A2']['content'] += (f" Currency: {currency}" if currency else "")
    periods = TIME[period_type]
    modified_periods = periods + 5 if period_type == 'month' else periods + 1
    for i in range(modified_periods):
        name_actual = COLUMNS[1 + NUMBER_COLUMN_PER_PERIOD * i]
        name_budget = COLUMNS[2 + NUMBER_COLUMN_PER_PERIOD * i]
        name_variance = COLUMNS[3 + NUMBER_COLUMN_PER_PERIOD * i]
        name_perf = COLUMNS[4 + NUMBER_COLUMN_PER_PERIOD * i]
        actual = {name_actual + k[-1]: v for (k, v) in col_actual.items()}
        budget = {name_budget + k[-1]: v for (k, v) in col_budget.items()}
        variance = {name_variance + k[-1]: v for (k, v) in col_variance.items()}
        perf = {name_perf + k[-1]: v for (k, v) in col_perf.items()}
        content = build_content(i, period_type, year)
        actual[f"{name_actual}3"] = {
            "content": content,
            "style": 9,
            "format": "#,##0.00"
        }
        sheet["col" + name_actual] = actual
        sheet["col" + name_budget] = budget
        sheet["col" + name_variance] = variance
        sheet["col" + name_perf] = perf
    return sheet


def generate_section_per_column(report_type, header, style_header, format_header, name_col, col, start, pivot,
                                period, loop, year, data_last_year=False, sign=1):
    """
    This function will generate formula and query data from each sections in one column
    INCOME, GROSS PROFIT, OPERATION INCOME,....

            A            B         C        D       E
            ------------------------------------------
    Header Net profit |  B5-B7..  | C5-C7  | B3-C3  |   B3/C3
           Depreciation| sum(B7:B12)| sum(C7:C12) | B4-C4 | B4/C4
           .....

    :param header:
    :param style_header:
    :param format_header:
    :param name_col:
    :param col:
    :param start:
    :param pivot:
    :param period:
    :param loop:
    :param year:
    :return:
    """
    pivot_id = pivot['pivot_id']
    res = {}
    other = {}
    res[col + str(start)] = {
        "content": str(header),
        "style": style_header,
        "format": format_header
    }
    period_time = f"0{period['time']}" if period['type'] == 'month' and type(period['time']) is int and period[
        'time'] <= 9 else period['time']
    time_range = range(1, 13) if period['type'] == 'month' else range(1, 5)
    for i in range(loop):
        if name_col == "name":
            formula = f"=PIVOT.HEADER(\"{pivot_id}\",\"account_id\",PIVOT.POSITION(\"{pivot_id}\",\"account_id\",{1 + i}))"
            other = {"style": 7}
        elif name_col == "actual":
            if type(period['time']) is str:
                formula = generate_formula_aggregation(period['time'], col, start + i + 1, period['type'])
            else:
                formula = f"=-PIVOT(\"{pivot_id}\",\"balance\",\"account_id\",PIVOT.POSITION(\"{pivot_id}\",\"account_id\",{i + 1}),\"date:{period['type']}\",\"{period_time}/{year}\")*{sign}"
            other = {"format": "#,##0.00"}
            # if report_type == 'balance':
            #     formula = generate_formula_balance_sheet(formula, period, year, pivot_id, i,
            #                                              max_time=period['time'], sign=sign)

        elif name_col == "budget":
            if data_last_year:
                if type(period['time']) is str:
                    formula = generate_formula_aggregation(period['time'], col, start + i + 1, period['type'])
                else:
                    formula = f"=-PIVOT(\"{pivot_id}\",\"balance\",\"account_id\",PIVOT.POSITION(\"{pivot_id}\",\"account_id\",{i + 1}),\"date:{period['type']}\",\"{period_time}/{year - 1}\")*{sign}"
                other = {"format": "#,##0.00"}
                # if report_type == 'balance':
                #     formula = generate_formula_balance_sheet("=", period, year-1, pivot_id, i,
                #                                              max_time=period['time']+1, sign=sign)
            else:
                if type(period['time']) is str:
                    formula = generate_formula_aggregation(period['time'], col, start + i + 1, period['type'])
                else:
                    formula = f"=0"
                other = {"format": "#,##0.00"}
        elif name_col == "variance":
            col1_idx, col2_idx = COLUMNS.index(col) - 2, COLUMNS.index(col) - 1
            col1, col2 = COLUMNS[col1_idx], COLUMNS[col2_idx]
            formula = f"={col1}{start + i + 1}-{col2}{start + i + 1}"
            other = {"format": "#,##0.00"}
        elif name_col == "perf":
            col1_idx, col2_idx = COLUMNS.index(col) - 3, COLUMNS.index(col) - 2
            col1, col2 = COLUMNS[col1_idx], COLUMNS[col2_idx]
            formula = f"=iferror({col1}{start + i + 1}/{col2}{start + i + 1},0)"
            other = {"format": "0.00%"}
        res[col + str(start + i + 1)] = {
            "content": formula,
        }
        res[col + str(start + i + 1)].update(other)
    return res


def generate_full_column(report_type, index_list, sheet, col, header, type_col, style_header, format_header, period,
                         pivots, year,
                         data_last_year=False, signs=[], num_of_rows_per_line=50):
    """

    :param index_list: list of header index
    :param sheet:
    :param col: A, B, C, D ....
    :param header: header for col A : [Net Profit, Depreciation,...], col B: [B5-B7, sum(B7:B12),..]
              A            B         C        D       E
            ------------------------------------------
    Header Net profit |  B5-B7..  | C5-C7  | B3-C3  |   B3/C3
           Depreciation| sum(B7:B12)| sum(C7:C12) | B4-C4 | B4/C4
           .....
    :param type_col: name, actual, budget,....
    :param style_header:
    :param format_header:
    :param period:
    :param pivots:
    :param year:
    :return:
    """

    sections = len(header)
    _start = start
    for i in range(sections):
        pivot = pivots[i]
        if not pivot['is_lowest']:
            param_col = generate_section_per_column(report_type=report_type, header=header[i], name_col=type_col,
                                                    col=col,
                                                    style_header=style_header,
                                                    format_header=format_header, start=_start, period=period,
                                                    pivot=pivot, loop=0, year=year, data_last_year=data_last_year,
                                                    sign=signs[i])
            _start += 1

        else:
            if type_col == 'name' or type_col == 'perf':
                param_col = generate_section_per_column(report_type=report_type, header=header[i], name_col=type_col,
                                                        col=col,
                                                        style_header=style_header,
                                                        format_header=format_header, start=_start, period=period,
                                                        pivot=pivot,
                                                        loop=num_of_rows_per_line, year=year,
                                                        data_last_year=data_last_year, sign=signs[i]
                                                        )
            else:
                s = index_list[i]
                header1 = f"=sum({col}{s + 1}:{col}{s + num_of_rows_per_line})"
                param_col = generate_section_per_column(report_type=report_type, header=header1, name_col=type_col,
                                                        col=col,
                                                        style_header=style_header,
                                                        format_header=format_header, start=_start, period=period,
                                                        pivot=pivot,
                                                        loop=num_of_rows_per_line, year=year,
                                                        data_last_year=data_last_year, sign=signs[i])
            _start += (num_of_rows_per_line + 1)
        column = sheet["col" + col]
        column.update(param_col)


def update_cell(lines, num_of_rows_per_line=50):
    count = start
    index_list = [count]
    for line in lines:
        line['cell'] = count
        if line['is_lowest']:
            count += (num_of_rows_per_line + 1)
        else:
            count += 1
        index_list.append(count)
    index_list.pop()
    return lines, index_list


def generate_spreadsheet_template(report_type, period_type, spreadsheet_name, lines_dict, year, analytic_account,
                                  create_budget_from_last_year, currency, num_of_rows_per_line=50):
    """
    This function generates json file which used to create spreadsheet.
    Json file will have similar structure as "quarterly_budget_spreadsheet_template.json" in
    documents_spreadsheet_account module
    We only generate "cells" and "pivots" keys in this json file based on parameter.
    :param period_type:
    :param spreadsheet_name:
    :param lines_dict:
    :param year:
    :return:

    """
    periods = {
        "type": period_type,
        "time": TIME[period_type]
    }
    year = int(year)
    cells = {}
    sheet = {}
    # Generate pivots
    pivots_list, pivots_in_sheet = generate_pivots(lines_dict, period_type, analytic_account)
    # Generate sheet
    sheet = generate_columns(sheet, period_type, spreadsheet_name, pivots_in_sheet, year, analytic_account, currency)
    lines, index_list = update_cell(lines_dict, num_of_rows_per_line)
    signs = [line['sign'] for line in lines_dict]

    ## Generate Account Column, Only generate once
    name_column = header_format[0]
    name_cell = COLUMNS[0]
    header = [l['name'] for l in lines]
    style_header = name_column['style_header']
    format_header = name_column['format_header']
    generate_full_column(report_type=report_type, index_list=index_list, sheet=sheet, col=name_cell, header=header,
                         type_col='name',
                         style_header=style_header,
                         format_header=format_header, period=periods, pivots=lines, year=year,
                         signs=signs, num_of_rows_per_line=num_of_rows_per_line)
    column = sheet["col" + name_cell]
    cells.update(column)
    # For each period of year, generate 4 columns Actual, Budget, Variace and Perf
    statistic_header_format = header_format[1:]
    modified_periods = periods['time'] + 5 if period_type == 'month' else periods['time'] + 1
    for i in range(modified_periods):
        for col_dict in statistic_header_format:
            step = col_dict['step']
            name = col_dict['col']
            col = COLUMNS[step + NUMBER_COLUMN_PER_PERIOD * i]  # A,B,C,D,E,F ...
            header = generate_formula_from_code_to_cell(name, col, lines)
            style_header = col_dict['style_header']
            format_header = col_dict['format_header']
            generate_full_column(
                report_type=report_type, index_list=index_list, sheet=sheet, col=col, header=header, type_col=name,
                style_header=style_header,
                format_header=format_header,
                period={'type': periods['type'], 'time': INDEX_TO_MONTH[periods['type']][i]},
                pivots=lines, year=year, data_last_year=create_budget_from_last_year, signs=signs,
                num_of_rows_per_line=num_of_rows_per_line)
            column = sheet["col" + col]
            cells.update(column)

    template_path = modules.get_module_resource('account_budget_spreadsheet', 'data/files', 'template.json')

    green_on_good, red_on_bad = build_condition_format(lines_dict, period_type,
                                                       green_on_positive=True), build_condition_format(lines_dict,
                                                                                                       period_type,
                                                                                                       green_on_positive=False)
    with open(template_path) as json_file:
        data = json.load(json_file).copy()
        data['pivots'] = pivots_list
        data['sheets'][0]['id'] = str(uuid.uuid1())
        data['sheets'][0]['cells'] = cells
        data['sheets'][0]['conditionalFormats'] = green_on_good + red_on_bad

        return data
