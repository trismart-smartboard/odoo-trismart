def get_barchart_format_overview(currency_name, data, label, color, order=0):
    return {
        'data': data,
        'label': label,
        'borderColor': color,
        'backgroundColor': color,
        'order': order,
        'currency': currency_name,
    }

def get_linechart_format_overview(currency_name, data, label, color, background_color=False, fill=False, border_width=2, line_tension=0, order=0):
    background_color = (background_color or color) if fill else '#fff'
    return {
        'data': data,
        'label': label,
        'borderColor': color,
        'backgroundColor': background_color,
        'borderWidth': border_width,
        'fill': fill,
        'lineTension': line_tension,
        'order': order,
        'type': 'line',
        'currency': currency_name,
    }

def get_chart_json_overview(currency_name, data, label, setting, info_data=[]):
    return {
        'data': data,
        'label': label,
        'setting': setting,
        'info_data': info_data,
        'currency': currency_name,
    }