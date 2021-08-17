#!/usr/bin/env python3
"""
Process report file from pylint into report which can be read by SonarQube.
The report file from pylint in parseable format which is at [1]
The output will follow the format given by SonarQube at [2]

[1] https://docs.pylint.org/en/1.6.0/output.html
[2] https://docs.sonarqube.org/latest/analysis/generic-issue/
"""

import re
import json
import argparse

VERSION = '1.0'

# pylint output format (parseable)
# More information available at [1]
PATH_REGEX = r'.+?'
LINE_REGEX = r'\d+'
MSG_ID_REGEX = r'[0-9A-Z]+'
SYMBOL_REGEX = r'[0-9A-Za-z_-]+'
OBJ_REGEX = r'[0-9A-Za-z_.-]+'
MSG_REGEX = r'.+?'
TMPL_REGEX = r'^({path}):({line}): \[({msg_id})\(({symbol})\), ({obj})?\] ({msg})$'.format(
    path=PATH_REGEX,
    line=LINE_REGEX,
    msg_id=MSG_ID_REGEX,
    symbol=SYMBOL_REGEX,
    obj=OBJ_REGEX,
    msg=MSG_REGEX,
)


def read_report(path: str):
    """
    Read report from `path` line by line and return potential issue line.
    An issue line is a line that contains filename, line number, message...
    """
    with open(path, 'r') as reader:
        line = reader.readline()
        while line:
            # The line which starts with this pattern ends the pylint report (only scores remain)
            if line.startswith('-' * 3):
                break
            formatted = line.strip()
            # Lines which start with this pattern indicate a filename, it is not needed
            if formatted and not formatted.startswith('*' * 3):
                yield formatted
            line = reader.readline()


def export_report(issues):
    """
    Process each issue on by one to generate the issue in the SonarQube's required format
    External issue format. See [2] for more information
    """
    for issue in issues:
        yield {
            'engineId': 'pylint_odoo',
            'ruleId': issue['msg_id'],
            'severity': 'MINOR',
            'type': 'CODE_SMELL',
            'effortMinutes': 60,
            'primaryLocation': {
                'message': issue['msg'],
                'filePath': issue['path'],
                'textRange': {
                    'startLine': int(issue['line'])
                }
            }
        }


def parse_report(path: str):
    """
    Read report from `path` line by line and check whether the line is an issue line
    If it is an issue, extract info from it
    """
    for line in read_report(path):
        match = re.findall(TMPL_REGEX, line)
        if match:
            match = match[0]
            yield {
                'path': match[0],
                'line': match[1],
                'msg_id': match[2],
                'symbol': match[3],
                'obj': match[4],
                'msg': match[5],
            }


def save_file(report: dict, path: str):
    """
    Save report to JSON file at `path`
    """
    with open(path, 'w') as output_file:
        json.dump(report, output_file, indent=2)


def run(path: str, output: str):
    """
    Run the main flow of the program
    """
    res = parse_report(path)
    # External issue format. See [2] for more information
    save_file({
        'issues': list(export_report(res))
    }, output)


def prepare_arg_parser():
    """
    Prepare Argument Parser for the program
    """
    desc = 'Process report file from pylint into report which can be read by SonarQube'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('path', type=str, help='Path to pylint report file')
    parser.add_argument('output', type=str, help='Path to output external issues file')
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {VERSION}')
    return parser.parse_args()

if __name__ == '__main__':
    args = prepare_arg_parser()
    run(args.path, args.output)
