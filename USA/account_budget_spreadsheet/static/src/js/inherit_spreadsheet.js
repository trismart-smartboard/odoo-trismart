// We need to inherit "updateCell" function of spreadsheet widget to handle error of no accounts.
// By default, if a section in report has no accounts, odoo will raise #Bad_Expression error in sheet.
// We will inherit "updateCell" function of spreadsheet widget to fill 0 value in section if it has no account by
// defining our new Error and handle when updateCell function catch it.

// We also need to inherit "tokenize" function of Odoo OOTB.
// By default, Odoo will catch an error if if the cell has more then 100 tokens. We will override "tokenize"
// to increase number of tokens allowed in a cell.
// => It is necessary to redefine and monkey-batch some methods and classes that uses tokenize function since
// tokenize is private in OOTB

// Workflow:
// User create spreadsheet from report => Odoo read and parse json file to generate cell
// => If section has no account => Odoo will parse the account into #Ref =>Inherit updateCell to catch error when
// value == #Ref => Assign cell to 0.
odoo.define("account_budget_spreadsheet.inherit_spreadsheet", function (require) {
    "use strict";


    const spreadsheet = require("documents_spreadsheet.spreadsheet")
    const spreadsheet_utils = require("account_budget_spreadsheet.o_spreadsheet_utils")
    const pivot_utils = require("documents_spreadsheet.pivot_utils")

    const pluginRegistry = spreadsheet.registries.pluginRegistry;

    var corePlugin = pluginRegistry.content['core']

    const {toXC, toCartesian} = spreadsheet.helpers;
    const {Spreadsheet} = spreadsheet;
    const Composer = Spreadsheet.components.Grid.components.Composer;
    const {
        parseNumber, parseDateTime, formatDateTime, compile, isNumber, _lt, _parse, RefError, _tokenize, enrichTokens,
        mergeSymbolsIntoRanges, toSimpleTokens, cellReference,mapParenthesis,tokenColor,rangeReference,
        getComposerSheetName,MatchingParenColor,colors
    } = spreadsheet_utils
    spreadsheet.parse = _parse;

    class ExtendComposer extends Composer {

        composerTokenize(formula) {
            const tokens = _tokenize(formula);
            return mergeSymbolsIntoRanges(mapParenthesis(enrichTokens(tokens)));
        }

        processContent() {
            this.shouldProcessInputEvents = false;
            let value = this.getters.getCurrentContent();
            this.tokenAtCursor = undefined;
            if (value.startsWith("=")) {
                this.saveSelection();
                this.contentHelper.removeAll(); // remove the content of the composer, to be added just after
                this.contentHelper.selectRange(0, 0); // move the cursor inside the composer at 0 0.
                this.dispatch("REMOVE_ALL_HIGHLIGHTS"); //cleanup highlights for references
                const refUsed = {};
                let lastUsedColorIndex = 0;
                this.tokens = this.composerTokenize(value);
                if (this.selectionStart === this.selectionEnd && this.selectionEnd === 0) {
                    this.tokenAtCursor = undefined;
                } else {
                    this.tokenAtCursor = this.tokens.find((t) => t.start <= this.selectionStart && t.end >= this.selectionEnd);
                }
                for (let token of this.tokens) {
                    switch (token.type) {
                        case "OPERATOR":
                        case "NUMBER":
                        case "FUNCTION":
                        case "COMMA":
                        case "BOOLEAN":
                            this.contentHelper.insertText(token.value, tokenColor[token.type]);
                            break;
                        case "SYMBOL":
                            let value = token.value;
                            const [xc, sheet] = value.split("!").reverse();
                            if (rangeReference.test(xc)) {
                                const refSanitized = getComposerSheetName(sheet
                                    ? `${sheet}`
                                    : `${this.getters.getSheetName(this.getters.getEditionSheet())}`) +
                                    "!" +
                                    xc.replace(/\$/g, "");
                                if (!refUsed[refSanitized]) {
                                    refUsed[refSanitized] = colors[lastUsedColorIndex];
                                    lastUsedColorIndex = ++lastUsedColorIndex % colors.length;
                                }
                                this.contentHelper.insertText(value, refUsed[refSanitized]);
                            } else {
                                this.contentHelper.insertText(value);
                            }
                            break;
                        case "LEFT_PAREN":
                        case "RIGHT_PAREN":
                            // Compute the matching parenthesis
                            if (this.tokenAtCursor &&
                                ["LEFT_PAREN", "RIGHT_PAREN"].includes(this.tokenAtCursor.type) &&
                                this.tokenAtCursor.parenIndex &&
                                this.tokenAtCursor.parenIndex === token.parenIndex) {
                                this.contentHelper.insertText(token.value, MatchingParenColor);
                            } else {
                                this.contentHelper.insertText(token.value);
                            }
                            break;
                        default:
                            this.contentHelper.insertText(token.value);
                            break;
                    }
                }
                // Put the cursor back where it was
                this.contentHelper.selectRange(this.selectionStart, this.selectionEnd);
                if (Object.keys(refUsed).length) {
                    this.dispatch("ADD_HIGHLIGHTS", {ranges: refUsed});
                }
            }
            this.shouldProcessInputEvents = true;
        }
    }

    class inheritedCorePlugin extends corePlugin {

        _rangeTokenize(formula) {
            const tokens = _tokenize(formula);
            return toSimpleTokens(mergeSymbolsIntoRanges(enrichTokens(tokens), true));
        }

        visitAllFormulasSymbols(cb) {
            for (let sheetId in this.workbook.sheets) {
                const sheet = this.workbook.sheets[sheetId];
                for (let [xc, cell] of Object.entries(sheet.cells)) {
                    if (cell.type === "formula") {
                        const content = this._rangeTokenize(cell.content)
                            .map((t) => {
                                if (t.type === "SYMBOL" && cellReference.test(t.value)) {
                                    return cb(t.value, sheet.id);
                                }
                                return t.value;
                            })
                            .join("");
                        if (content !== cell.content) {
                            const [col, row] = toCartesian(xc);
                            this.dispatch("UPDATE_CELL", {
                                sheet: sheet.id,
                                col,
                                row,
                                content,
                            });
                        }
                    }
                }
            }
        }

        updateCell(sheet, col, row, data) {
            const nbspRegexp = new RegExp(String.fromCharCode(160), "g");
            const _sheet = this.workbook.sheets[sheet];
            const current = _sheet.rows[row].cells[col];
            const xc = (current && current.xc) || toXC(col, row);
            const hasContent = "content" in data;
            // Compute the new cell properties
            const dataContent = data.content ? data.content.replace(nbspRegexp, "") : "";
            let content = hasContent ? dataContent : (current && current.content) || "";
            const style = "style" in data ? data.style : (current && current.style) || 0;
            const border = "border" in data ? data.border : (current && current.border) || 0;
            let format = "format" in data ? data.format : (current && current.format) || "";
            // if all are empty, we need to delete the underlying cell object
            if (!content && !style && !border && !format) {
                if (current) {
                    // todo: make this work on other sheets
                    this.history.updateSheet(_sheet, ["cells", xc], undefined);
                    this.history.updateSheet(_sheet, ["rows", row, "cells", col], undefined);
                }
                return;
            }
            // compute the new cell value
            const didContentChange = (!current && dataContent) || (hasContent && current && current.content !== dataContent);
            let cell;
            if (current && !didContentChange) {
                cell = {col, row, xc, content, value: current.value, type: current.type};
                if (cell.type === "formula") {
                    cell.error = current.error;
                    cell.pending = current.pending;
                    cell.formula = current.formula;
                    if (current.async) {
                        cell.async = true;
                    }
                }
            } else {
                // the current content cannot be reused, so we need to recompute the
                // derived values
                let type = content[0] === "=" ? "formula" : "text";
                let value = content;
                if (isNumber(content)) {
                    value = parseNumber(content);
                    type = "number";
                    if (content.includes("%")) {
                        format = content.includes(".") ? "0.00%" : "0%";
                    }
                }
                let date = parseDateTime(content);
                if (date) {
                    type = "date";
                    value = date;
                    content = formatDateTime(date);
                }
                const contentUpperCase = content.toUpperCase();
                if (contentUpperCase === "TRUE") {
                    value = true;
                }
                if (contentUpperCase === "FALSE") {
                    value = false;
                }
                cell = {col, row, xc, content, value, type};
                if (cell.type === "formula") {
                    cell.error = undefined;
                    try {
                        cell.formula = compile(content, sheet, this.sheetIds);
                        cell.async = cell.formula.async;
                    } catch (e) {
                        if (e instanceof RefError) {
                            cell.value = '=0';
                            cell.type = "number";
                            cell.content = '=0';
                        } else {
                            cell.value = "#BAD_EXPR";
                            cell.error = _lt("Invalid Expression");
                        }
                    }
                }
            }
            if (style) {
                cell.style = style;
            }
            if (border) {
                cell.border = border;
            }
            if (format) {
                cell.format = format;
            }
            // todo: make this work on other sheets
            this.history.updateSheet(_sheet, ["cells", xc], cell);
            this.history.updateSheet(_sheet, ["rows", row, "cells", col], cell);
        }
    }

    Spreadsheet.components.Grid.components.Composer = ExtendComposer;
    pluginRegistry.add('core', inheritedCorePlugin);
    spreadsheet.registries.pluginRegistry = pluginRegistry;

});
