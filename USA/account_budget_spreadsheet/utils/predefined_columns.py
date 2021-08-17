COLUMNS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V",
           "W", "X", "Y", "Z",
           "AA", "AB", "AC", "AD", "AE", "AF", "AG", "AH", "AI", "AJ", "AK", "AL", "AM", "AN", "AO", "AP", "AQ", "AR",
           "AS", "AT", "AU", "AV", "AW", "AX", "AY", "AZ",
           "BA", "BB", "BC", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BK", "BL", "BM", "BN", "BO", "BP", "BQ", "BR",
           "BS", "BT", "BU", "BV", "BW", "BX", "BY", "BZ",
           ]

POSITIVE_TEXT_COLOR = "#365624"
POSITIVE_FILL_COLOR = "#e3efd9"
NEGATIVE_TEXT_COLOR = "#8c1003"
NEGATIVE_FILL_COLOR = "#f2cdc9"

col_name = {
    "A1": {
        "content": "=\"Quarterly Budget Report - \"&FILTER.VALUE(\"Year\")",
        "style": 22
    },
    "A2": {
        "content": "",
        "style": 23
    },
    "A3": {
        "content": "",
        "style": 3
    },
    "A4": {
        "content": "",
        "style": 7
    }
}
col_actual = {
    "cell1": {
        "content": "",
        "style": 23,
        "format": "#,##0.00"
    },
    "cell2": {
        "content": "",
        "style": 23,
        "format": "#,##0.00"
    },
    "cell3": {
        "content": "=PIVOT.HEADER(\"1\",\"date:quarter\",\"1/\"&FILTER.VALUE(\"Year\"))",
        "style": 9,
        "format": "#,##0.00"
    },
    "cell4": {
        "content": "Actuals",
        "style": 14,
        "format": "#,##0.00"
    }
}
col_budget = {
    "cell1": {
        "content": "",
        "style": 23,
        "format": "#,##0.00"
    },
    "cell2": {
        "content": "",
        "style": 23,
        "format": "#,##0.00"
    },
    "cell3": {
        "content": "",
        "style": 9,
        "format": "#,##0.00"
    },
    "cell4": {
        "content": "Budget",
        "style": 14,
        "format": "#,##0.00"
    }
}
col_variance = {
    "cell1": {
        "content": "",
        "style": 23,
        "format": "#,##0.00"
    },
    "cell2": {
        "content": "",
        "style": 23,
        "format": "#,##0.00"
    },
    "cell3": {
        "content": "",
        "style": 9,
        "format": "#,##0.00"
    },
    "cell4": {
        "content": "Variance",
        "style": 14,
        "format": "#,##0.00"
    }
}
col_perf = {
    "cell1": {
        "content": "",
        "style": 23,
        "format": "0.00%"
    },
    "cell2": {
        "content": "",
        "style": 23,
        "format": "0.00%"
    },
    "cell3": {
        "content": "",
        "style": 9,
        "format": "0.00"
    },
    "cell4": {
        "content": "Perf.",
        "style": 14,
        "format": "0.00%"
    }
}

header_format = [
    {
        'col': 'name',
        'style_header': 3,
        'format_header': None,
        'step': 0,
    },
    {
        'col': 'actual',
        'style_header': 3,
        'format_header': "#,##0.00",
        'step': 1,
    },
    {
        'col': 'budget',
        'style_header': 3,
        'format_header': "#,##0.00",
        'step': 2,
    },
    {
        'col': 'variance',
        'style_header': 3,
        'format_header': "#,##0.00",
        'step': 3,
    },
    {
        'col': 'perf',
        "style_header": 3,
        "format_header": "0.00%",
        'step': 4,
    }
]
