#!/bin/sh
PROJECT_NAME=$1
REPORT_NAME="${PROJECT_NAME}_pylint_report.txt"

pylint --generate-rcfile > pylint_rcfile.txt
find . -maxdepth 1 -type d -not -path './\.*' -not -name 'sonarqube_report' -not -name '.' | xargs pylint --rcfile=./pylint_rcfile.txt -r n --load-plugins=pylint_odoo -d all -e odoolint -d manifest-required-author,incoherent-interpreter-exec-perm --exit-zero --output-format=parseable > "${REPORT_NAME}"
