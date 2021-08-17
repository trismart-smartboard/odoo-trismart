pivot_template = {
            "model": "account.move.line",
            "rowGroupBys": [
                "account_id"
            ],
            "colGroupBys": [
                "date:quarter"
            ],
            "measures": [
                {
                    "field": "balance",
                    "operator": "sum"
                }
            ],
            "domain": [
                          "&",
                          "&",
                          [
                              "display_type",
                              "not in",
                              [
                                  "line_section",
                                  "line_note"
                              ]
                          ],
                          [
                              "move_id.state",
                              "!=",
                              "cancel"
                          ],
                          "&",
                          [
                              "move_id.state",
                              "=",
                              "posted"
                          ]

                      ],
            "context": {
                "lang": "en_US",
                "tz": "Europe/Brussels",
                "uid": 2,
                "allowed_company_ids": [
                    1
                ],
                "journal_type": "general",
                "search_default_posted": 1,
                "pivot_measures": [
                    "balance"
                ],
                "pivot_column_groupby": [
                    f"date:quarter"
                ],
                "pivot_row_groupby": [
                    "account_id"
                ],
                "budget_spreadsheet": True
            },
            "id": 1,
            "isLoaded": False,
            "promise": {}
        }