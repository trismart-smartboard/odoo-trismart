// Helper functions of spreadsheet widget we use in updateCell function

odoo.define("account_budget_spreadsheet.o_spreadsheet_utils", function (require) {
        "use strict";

        const functionCache = {};
        const AsyncFunction = Object.getPrototypeOf(async function () {
        }).constructor;

        const spreadsheet = require("documents_spreadsheet.spreadsheet");
        const {toNumber, toXC, toCartesian} = spreadsheet.helpers;
        const functionRegistry = spreadsheet.registries.functionRegistry
        const functions$3 = functionRegistry.content;
        const functions$2 = functionRegistry.content;
        const functions$1 = functionRegistry.content;

        // Regex Constants
        const commaRegexp = /,/g;
        const timeRegexp = /((\d+(:\d+)?(:\d+)?\s*(AM|PM))|(\d+:\d+(:\d+)?))$/;
        const mdyDateRegexp = /^\d{1,2}(\/|-|\s)\d{1,2}((\/|-|\s)\d{1,4})?$/;
        const ymdDateRegexp = /^\d{3,4}(\/|-|\s)\d{1,2}(\/|-|\s)\d{1,2}$/;
        const numberRegexp = /^-?\d+(,\d+)*(\.?\d*(e\d+)?)?(\s*%)?$|^-?\.\d+(\s*%)?$/;
        const cellReference = new RegExp(/\$?[A-Z]+\$?[0-9]+/, "i");
        const whiteSpaceRegexp = /\s/;
        const formulaNumberRegexp = /^-?\d+(\.?\d*(e\d+)?)?(\s*%)?|^-?\.\d+(\s*%)?/;
        const separatorRegexp = /\w|\.|!|\$/;
        const rangeReference = new RegExp(/^\s*\$?[A-Z]+\$?[0-9]+\s*(\s*:\s*\$?[A-Z]+\$?[0-9]+\s*)?$/, "i");

        //Constant
        const FUNCTION_BP = 6;
        const CURRENT_MILLENIAL = 2000;
        const INITIAL_JS_DAY = new Date(0);
        const INITIAL_1900_DAY = new Date(1899, 11, 30);
        const DATE_JS_1900_OFFSET = INITIAL_JS_DAY - INITIAL_1900_DAY;
        const CURRENT_YEAR = new Date().getFullYear();
        const OPERATOR_MAP = {
            "=": "EQ",
            "+": "ADD",
            "-": "MINUS",
            "*": "MULTIPLY",
            "/": "DIVIDE",
            ">=": "GTE",
            "<>": "NE",
            ">": "GT",
            "<=": "LTE",
            "<": "LT",
            "^": "POWER",
            "&": "CONCATENATE",
        };
        const UNARY_OPERATOR_MAP = {
            "-": "UMINUS",
            "+": "UPLUS",
        };
        const OP_PRIORITY = {
            "^": 30,
            "*": 20,
            "/": 20,
            ">": 10,
            "<>": 10,
            ">=": 10,
            "<": 10,
            "<=": 10,
            "=": 10,
            "-": 7,
        };
        const UNARY_OPERATORS = ["-", "+"];
        const OPERATORS = "+,-,*,/,:,=,<>,>=,>,<=,<,%,^,&".split(",");
        const misc = {
            ",": "COMMA",
            "(": "LEFT_PAREN",
            ")": "RIGHT_PAREN",
        };
        const colors = [
            "#ff851b",
            "#0074d9",
            "#ffdc00",
            "#7fdbff",
            "#b10dc9",
            "#0ecc40",
            "#39cccc",
            "#f012be",
            "#3d9970",
            "#111111",
            "#01ff70",
            "#ff4136",
            "#aaaaaa",
            "#85144b",
            "#001f3f",
        ];

        const FunctionColor = "#4a4e4d";
        const OperatorColor = "#3da4ab";
        const StringColor = "#f6cd61";
        const NumberColor = "#02c39a";
        const MatchingParenColor = "pink";
        const tokenColor = {
            OPERATOR: OperatorColor,
            NUMBER: NumberColor,
            STRING: StringColor,
            BOOLEAN: NumberColor,
            FUNCTION: FunctionColor,
            DEBUGGER: OperatorColor,
            LEFT_PAREN: OperatorColor,
            RIGHT_PAREN: OperatorColor,
        };


        let _t = (s) => s;
        const _lt = function (s) {
            return {
                toString: function () {
                    return _t(s);
                },
            };
        };

        //User-defined Error
        function RefError(message = "") {
            this.name = "NotImplementedError";
            this.message = message;
        }

        ///////////////////
        // Helper Function to format datetime
        ///////////////////
        function getUnquotedSheetName(sheetName) {
            if (sheetName.startsWith("'")) {
                sheetName = sheetName.slice(1, -1).replace(/''/g, "'");
            }
            return sheetName;
        }

        function formatJSDate(date, format) {
            const sep = format.match(/\/|-|\s/)[0];
            const parts = format.split(sep);
            return parts
                .map((p) => {
                    switch (p) {
                        case "d":
                            return date.getDate();
                        case "dd":
                            return date.getDate().toString().padStart(2, "0");
                        case "m":
                            return date.getMonth() + 1;
                        case "mm":
                            return String(date.getMonth() + 1).padStart(2, "0");
                        case "yyyy":
                            return date.getFullYear();
                        default:
                            throw new Error(_lt("invalid format"));
                    }
                })
                .join(sep);
        }

        function formatJSTime(date, format) {
            let parts = format.split(/:|\s/);
            const dateHours = date.getHours();
            const isMeridian = parts[parts.length - 1] === "a";
            let hours = dateHours;
            let meridian = "";
            if (isMeridian) {
                hours = hours === 0 ? 12 : hours > 12 ? hours - 12 : hours;
                meridian = dateHours >= 12 ? " PM" : " AM";
                parts.pop();
            }
            return (parts
                .map((p) => {
                    switch (p) {
                        case "hhhh":
                            const helapsedHours = Math.floor((date.getTime() - INITIAL_1900_DAY) / (60 * 60 * 1000));
                            return helapsedHours.toString();
                        case "hh":
                            return hours.toString().padStart(2, "0");
                        case "mm":
                            return date.getMinutes().toString().padStart(2, "0");
                        case "ss":
                            return date.getSeconds().toString().padStart(2, "0");
                        default:
                            throw new Error("invalid format");
                    }
                })
                .join(":") + meridian);
        }

        function numberToDate(value) {
            const truncValue = Math.trunc(value);
            let date = new Date(truncValue * 86400 * 1000 - DATE_JS_1900_OFFSET);
            let time = value - truncValue;
            time = time < 0 ? 1 + time : time;
            const hours = Math.round(time * 24);
            const minutes = Math.round((time - hours / 24) * 24 * 60);
            const seconds = Math.round((time - hours / 24 - minutes / 24 / 60) * 24 * 60 * 60);
            date.setHours(hours);
            date.setMinutes(minutes);
            date.setSeconds(seconds);
            return date;
        }

        function toNativeDate(date) {
            if (typeof date === "object" && date !== null) {
                if (!date.jsDate) {
                    date.jsDate = new Date(date.value * 86400 * 1000 - DATE_JS_1900_OFFSET);
                }
                return date.jsDate;
            }
            if (typeof date === "string") {
                let result = parseDateTime(date);
                if (result !== null && result.jsDate) {
                    return result.jsDate;
                }
            }
            return numberToDate(toNumber(date));
        }

        function formatDateTime(date, format) {
            // TODO: unify the format functions for date and datetime
            // This requires some code to 'parse' or 'tokenize' the format, keep it in a
            // cache, and use it in a single mapping, that recognizes the special list
            // of tokens dd,d,m,y,h, ... and preserves the rest
            const dateTimeFormat = format || date.format;
            const jsDate = toNativeDate(date);
            const indexH = dateTimeFormat.indexOf("h");
            let strDate = "";
            let strTime = "";
            if (indexH > 0) {
                strDate = formatJSDate(jsDate, dateTimeFormat.substring(0, indexH - 1));
                strTime = formatJSTime(jsDate, dateTimeFormat.substring(indexH));
            } else if (indexH === 0) {
                strTime = formatJSTime(jsDate, dateTimeFormat);
            } else if (indexH < 0) {
                strDate = formatJSDate(jsDate, dateTimeFormat);
            }
            return strDate + (strDate && strTime ? " " : "") + strTime;
        }

        function inferYear(str) {
            const nbr = Number(str);
            switch (str.length) {
                case 1:
                    return CURRENT_MILLENIAL + nbr;
                case 2:
                    const offset = CURRENT_MILLENIAL + nbr > CURRENT_YEAR + 10 ? -100 : 0;
                    const base = CURRENT_MILLENIAL + offset;
                    return base + nbr;
                case 3:
                case 4:
                    return nbr;
            }
            return 0;
        }

        function parseTime(str) {
            str = str.trim();
            if (timeRegexp.test(str)) {
                const isAM = /AM/i.test(str);
                const isPM = /PM/i.test(str);
                const strTime = isAM || isPM ? str.substring(0, str.length - 2).trim() : str;
                const parts = strTime.split(/:/);
                const isMinutes = parts.length >= 2;
                const isSeconds = parts.length === 3;
                let hours = Number(parts[0]);
                let minutes = isMinutes ? Number(parts[1]) : 0;
                let seconds = isSeconds ? Number(parts[2]) : 0;
                let format = isSeconds ? "hh:mm:ss" : "hh:mm";
                if (isAM || isPM) {
                    format += " a";
                } else if (!isMinutes) {
                    return null;
                }
                if (hours >= 12 && isAM) {
                    hours -= 12;
                } else if (hours < 12 && isPM) {
                    hours += 12;
                }
                minutes += Math.floor(seconds / 60);
                seconds %= 60;
                hours += Math.floor(minutes / 60);
                minutes %= 60;
                if (hours >= 24) {
                    format = "hhhh:mm:ss";
                }
                const jsDate = new Date(1899, 11, 30, hours, minutes, seconds);
                return {
                    value: hours / 24 + minutes / 1440 + seconds / 86400,
                    format: format,
                    jsDate: jsDate,
                };
            }
            return null;
        }

        function parseNumber(str) {
            let n = Number(str.replace(commaRegexp, ""));
            if (isNaN(n) && str.includes("%")) {
                n = Number(str.split("%")[0]);
                if (!isNaN(n)) {
                    return n / 100;
                }
            }
            return n;
        }

        function isNumber(value) {
            // TO DO: add regexp for DATE string format (ex match: "28 02 2020")
            return numberRegexp.test(value.trim());
        }

        function parseDate(str, dateFormat) {
            const isMDY = dateFormat === "mdy";
            const isYMD = dateFormat === "ymd";
            if (isMDY || isYMD) {
                const parts = str.split(/\/|-|\s/);
                const monthIndex = isMDY ? 0 : 1;
                const dayIndex = isMDY ? 1 : 2;
                const yearIndex = isMDY ? 2 : 0;
                const month = Number(parts[monthIndex]);
                const day = Number(parts[dayIndex]);
                const leadingZero = (parts[monthIndex].length === 2 && month < 10) || (parts[dayIndex].length === 2 && day < 10);
                const year = parts[yearIndex] ? inferYear(parts[yearIndex]) : CURRENT_YEAR;
                const jsDate = new Date(year, month - 1, day);
                const sep = str.match(/\/|-|\s/)[0];
                if (jsDate.getMonth() !== month - 1 || jsDate.getDate() !== day) {
                    // invalid date
                    return null;
                }
                const delta = jsDate - INITIAL_1900_DAY;
                let format = leadingZero ? `mm${sep}dd` : `m${sep}d`;
                if (parts[yearIndex]) {
                    format = isMDY ? format + sep + "yyyy" : "yyyy" + sep + format;
                }
                return {
                    value: Math.round(delta / 86400000),
                    format: format,
                    jsDate,
                };
            }
            return null;
        }

        function parseDateTime(str) {
            str = str.trim();
            let time;
            const timeMatch = str.match(timeRegexp);
            if (timeMatch) {
                time = parseTime(timeMatch[0]);
                if (time === null) {
                    return null;
                }
                str = str.replace(timeMatch[0], "").trim();
            }
            let date;
            const mdyDateMatch = str.match(mdyDateRegexp);
            const ymdDateMatch = str.match(ymdDateRegexp);
            if (mdyDateMatch || ymdDateMatch) {
                let dateMatch;
                if (mdyDateMatch) {
                    dateMatch = mdyDateMatch[0];
                    date = parseDate(dateMatch, "mdy");
                } else {
                    dateMatch = ymdDateMatch[0];
                    date = parseDate(dateMatch, "ymd");
                }
                if (date === null) {
                    return null;
                }
                str = str.replace(dateMatch, "").trim();
            }
            if (str !== "" || !(date || time)) {
                return null;
            }
            if (date && time) {
                return {
                    value: date.value + time.value,
                    format: date.format + " " + (time.format === "hhhh:mm:ss" ? "hh:mm:ss" : time.format),
                    jsDate: new Date(date.jsDate.getFullYear() + time.jsDate.getFullYear() - 1899, date.jsDate.getMonth() + time.jsDate.getMonth() - 11, date.jsDate.getDate() + time.jsDate.getDate() - 30, date.jsDate.getHours() + time.jsDate.getHours(), date.jsDate.getMinutes() + time.jsDate.getMinutes(), date.jsDate.getSeconds() + time.jsDate.getSeconds()),
                };
            }
            return date || time;
        }

        ///////////////////
        // Helper Function to tokenize,compile and parse code to cell.
        ///////////////////
        function compile(str, sheet, sheets) {
            const ast = _parse(str);
            let nextId = 1;
            const code = [`// ${str}`];
            let isAsync = false;
            let cacheKey = "";
            let cellRefs = [];
            let rangeRefs = [];
            if (ast.type === "BIN_OPERATION" && ast.value === ":") {
                throw new Error(_lt("Invalid formula"));
            }
            if (ast.type === "UNKNOWN") {
                throw new Error(_lt("Invalid formula"));
            }

            /**
             * This function compile the function arguments. It is mostly straightforward,
             * except that there is a non trivial transformation in one situation:
             *
             * If a function argument is asking for a range, and get a cell, we transform
             * the cell value into a range. This allow the grid model to differentiate
             * between a cell value and a non cell value.
             */
            function compileFunctionArgs(ast) {
                const fn = functions$3[ast.value.toUpperCase()];
                const result = [];
                const args = ast.args;
                let argDescr;
                for (let i = 0; i < args.length; i++) {
                    const arg = args[i];
                    argDescr = fn.args[i] || argDescr;
                    const isLazy = argDescr && argDescr.lazy;
                    let argValue = compileAST(arg, isLazy);
                    if (arg.type === "REFERENCE") {
                        const types = argDescr.type;
                        const hasRange = types.find((t) => t === "RANGE" ||
                            t === "RANGE<BOOLEAN>" ||
                            t === "RANGE<NUMBER>" ||
                            t === "RANGE<STRING>");
                        if (hasRange) {
                            argValue = `[[${argValue}]]`;
                        }
                    }
                    result.push(argValue);
                }
                const isRepeating = fn.args.length ? fn.args[fn.args.length - 1].repeating : false;
                let minArg = 0;
                let maxArg = isRepeating ? Infinity : fn.args.length;
                for (let arg of fn.args) {
                    if (!arg.optional) {
                        minArg++;
                    }
                }
                if (result.length < minArg || result.length > maxArg) {
                    throw new Error(_lt(`
          Invalid number of arguments for the ${ast.value.toUpperCase()} function.
          Expected ${fn.args.length}, but got ${result.length} instead.`));
                }
                return result;
            }

            function compileAST(ast, isLazy = false) {
                let id, left, right, args, fnName, statement;
                if (ast.type !== "REFERENCE" && !(ast.type === "BIN_OPERATION" && ast.value === ":")) {
                    cacheKey += "_" + ast.value;
                }
                if (ast.debug) {
                    cacheKey += "?";
                    code.push("debugger;");
                }
                switch (ast.type) {
                    case "BOOLEAN":
                    case "NUMBER":
                    case "STRING":
                        if (!isLazy) {
                            return ast.value;
                        }
                        id = nextId++;
                        statement = `${ast.value}`;
                        break;
                    case "REFERENCE":
                        id = nextId++;
                        cacheKey += "__REF";
                        const sheetId = ast.sheet ? sheets[ast.sheet] : sheet;
                        const refIdx = cellRefs.push([ast.value, sheetId]) - 1;
                        statement = `cell(${refIdx})`;
                        break;
                    case "FUNCALL":
                        id = nextId++;
                        args = compileFunctionArgs(ast);
                        fnName = ast.value.toUpperCase();
                        code.push(`ctx.__lastFnCalled = '${fnName}'`);
                        statement = `ctx['${fnName}'](${args})`;
                        break;
                    case "ASYNC_FUNCALL":
                        id = nextId++;
                        isAsync = true;
                        args = compileFunctionArgs(ast);
                        fnName = ast.value.toUpperCase();
                        code.push(`ctx.__lastFnCalled = '${fnName}'`);
                        statement = `await ctx['${fnName}'](${args})`;
                        break;
                    case "UNARY_OPERATION":
                        id = nextId++;
                        right = compileAST(ast.right);
                        fnName = UNARY_OPERATOR_MAP[ast.value];
                        code.push(`ctx.__lastFnCalled = '${fnName}'`);
                        statement = `ctx['${fnName}']( ${right})`;
                        break;
                    case "BIN_OPERATION":
                        id = nextId++;
                        if (ast.value === ":") {
                            cacheKey += "__RANGE";
                            const sheetName = ast.left.type === "REFERENCE" && ast.left.sheet;
                            const sheetId = sheetName ? sheets[sheetName] : sheet;
                            const rangeIdx = rangeRefs.push([ast.left.value, ast.right.value, sheetId]) - 1;
                            statement = `range(${rangeIdx});`;
                        } else {
                            left = compileAST(ast.left);
                            right = compileAST(ast.right);
                            fnName = OPERATOR_MAP[ast.value];
                            code.push(`ctx.__lastFnCalled = '${fnName}'`);
                            statement = `ctx['${fnName}'](${left}, ${right})`;
                        }
                        break;
                    case "UNKNOWN":
                        if (!isLazy) {
                            return "null";
                        }
                        id = nextId++;
                        statement = `null`;
                        break;
                }
                code.push(`let _${id} = ` + (isLazy ? `()=> ` : ``) + statement);
                return `_${id}`;
            }

            code.push(`return ${compileAST(ast)};`);
            let baseFunction = functionCache[cacheKey];
            if (!baseFunction) {
                const Constructor = isAsync ? AsyncFunction : Function;
                baseFunction = new Constructor("cell", "range", "ctx", code.join("\n"));
                functionCache[cacheKey] = baseFunction;
            }
            const resultFn = (cell, range, ctx) => {
                const cellFn = (idx) => {
                    const [xc, sheetId] = cellRefs[idx];
                    return cell(xc, sheetId);
                };
                const rangeFn = (idx) => {
                    const [xc1, xc2, sheetId] = rangeRefs[idx];
                    return range(xc1, xc2, sheetId);
                };
                return baseFunction(cellFn, rangeFn, ctx);
            };
            resultFn.async = isAsync;
            return resultFn;
        }

        function bindingPower(token) {
            switch (token.type) {
                case "NUMBER":
                case "SYMBOL":
                    return 0;
                case "COMMA":
                    return 3;
                case "LEFT_PAREN":
                    return 5;
                case "RIGHT_PAREN":
                    return 5;
                case "OPERATOR":
                    return OP_PRIORITY[token.value] || 15;
            }
            throw new Error(_lt("?"));
        }

        function _tokenize(str) {
            const chars = str.split("");
            const result = [];
            let tokenCount = 0;
            while (chars.length) {
                tokenCount++;

                if (tokenCount > 2000) {
                    throw new Error(_lt("This formula has over 100 parts. It can't be processed properly, consider splitting it into multiple cells"));
                }
                let token = tokenizeSpace(chars) ||
                    tokenizeMisc(chars) ||
                    tokenizeOperator(chars) ||
                    tokenizeNumber(chars) ||
                    tokenizeString(chars) ||
                    tokenizeDebugger(chars) ||
                    tokenizeSymbol(chars);
                if (!token) {
                    token = {type: "UNKNOWN", value: chars.shift()};
                }
                result.push(token);
            }
            return result;
        }

        function parsePrefix(current, tokens) {
            switch (current.type) {
                case "DEBUGGER":
                    const next = parseExpression(tokens, 1000);
                    next.debug = true;
                    return next;
                case "NUMBER":
                    return {type: current.type, value: parseNumber(current.value)};
                case "STRING":
                    return {type: current.type, value: current.value};
                case "FUNCTION":
                    if (tokens.shift().type !== "LEFT_PAREN") {
                        throw new Error(_lt("wrong function call"));
                    } else {
                        const args = [];
                        if (tokens[0].type !== "RIGHT_PAREN") {
                            if (tokens[0].type === "COMMA") {
                                args.push({type: "UNKNOWN", value: ""});
                            } else {
                                args.push(parseExpression(tokens, FUNCTION_BP));
                            }
                            while (tokens[0].type === "COMMA") {
                                tokens.shift();
                                if (tokens[0].type === "RIGHT_PAREN") {
                                    args.push({type: "UNKNOWN", value: ""});
                                    break;
                                }
                                if (tokens[0].type === "COMMA") {
                                    args.push({type: "UNKNOWN", value: ""});
                                } else {
                                    args.push(parseExpression(tokens, FUNCTION_BP));
                                }
                            }
                        }
                        if (tokens.shift().type !== "RIGHT_PAREN") {
                            throw new Error(_lt("wrong function call"));
                        }
                        const isAsync = functions$2[current.value.toUpperCase()].async;
                        const type = isAsync ? "ASYNC_FUNCALL" : "FUNCALL";
                        return {type, value: current.value, args};
                    }
                case "SYMBOL":
                    if (cellReference.test(current.value)) {
                        if (current.value.includes("!")) {
                            let [sheet, val] = current.value.split("!");
                            sheet = getUnquotedSheetName(sheet);
                            return {
                                type: "REFERENCE",
                                value: val.replace(/\$/g, "").toUpperCase(),
                                sheet: sheet,
                            };
                        } else {
                            return {
                                type: "REFERENCE",
                                value: current.value.replace(/\$/g, "").toUpperCase(),
                            };
                        }
                    } else {
                        if (["TRUE", "FALSE"].includes(current.value.toUpperCase())) {
                            return {type: "BOOLEAN", value: current.value.toUpperCase() === "TRUE"};
                        } else {
                            if (current.value) {
                                throw new Error(_lt("Invalid formula"));
                            }
                            return {type: "UNKNOWN", value: current.value};
                        }
                    }
                case "LEFT_PAREN":
                    const result = parseExpression(tokens, 5);
                    if (!tokens.length || tokens[0].type !== "RIGHT_PAREN") {
                        throw new Error(_lt("unmatched left parenthesis"));
                    }
                    tokens.shift();
                    return result;
                default:
                    if (current.type === "OPERATOR" && UNARY_OPERATORS.includes(current.value)) {
                        return {
                            type: "UNARY_OPERATION",
                            value: current.value,
                            right: parseExpression(tokens, 15),
                        };
                    }
                    if (current.type === "UNKNOWN" && current.value === "#") {
                        throw new RefError("Invalid Reference");
                    }
                    throw new Error(_lt("nope")); //todo: provide explicit error
            }
        }

        function parseInfix(left, current, tokens) {
            if (current.type === "OPERATOR") {
                const bp = bindingPower(current);
                const right = parseExpression(tokens, bp);
                if (current.value === ":") {
                    if (left.type === "REFERENCE" && right.type === "REFERENCE") {
                        const [x1, y1] = toCartesian(left.value);
                        const [x2, y2] = toCartesian(right.value);
                        left.value = toXC(Math.min(x1, x2), Math.min(y1, y2));
                        right.value = toXC(Math.max(x1, x2), Math.max(y1, y2));
                    }
                }
                return {
                    type: "BIN_OPERATION",
                    value: current.value,
                    left,
                    right,
                };
            }
            throw new Error(_lt("nope")); //todo: provide explicit error
        }

        function parseExpression(tokens, bp) {
            const token = tokens.shift();
            let expr = parsePrefix(token, tokens);
            while (tokens[0] && bindingPower(tokens[0]) > bp) {
                expr = parseInfix(expr, tokens.shift(), tokens);
            }
            return expr;
        }

        function _parse(str) {
            const tokens = _tokenize(str).filter((x) => x.type !== "SPACE");
            if (tokens[0].type === "OPERATOR" && tokens[0].value === "=") {
                tokens.splice(0, 1);
            }
            const result = parseExpression(tokens, 0);
            if (tokens.length) {
                throw new Error(_lt("invalid expression"));
            }
            return result;
        }


        function tokenizeSpace(chars) {
            let length = 0;
            while (chars[0] && chars[0].match(whiteSpaceRegexp)) {
                length++;
                chars.shift();
            }
            if (length) {
                return {type: "SPACE", value: " ".repeat(length)};
            }
            return null;
        }

        function tokenizeDebugger(chars) {
            if (chars[0] === "?") {
                chars.shift();
                return {type: "DEBUGGER", value: "?"};
            }
            return null;
        }


        function tokenizeMisc(chars) {
            if (chars[0] in misc) {
                const value = chars.shift();
                const type = misc[value];
                return {type, value};
            }
            return null;
        }

        function startsWith(chars, op) {
            for (let i = 0; i < op.length; i++) {
                if (op[i] !== chars[i]) {
                    return false;
                }
            }
            return true;
        }

        function tokenizeOperator(chars) {
            for (let op of OPERATORS) {
                if (startsWith(chars, op)) {
                    chars.splice(0, op.length);
                    return {type: "OPERATOR", value: op};
                }
            }
            return null;
        }

        function tokenizeNumber(chars) {
            const match = chars.join("").match(formulaNumberRegexp);
            if (match) {
                chars.splice(0, match[0].length);
                return {type: "NUMBER", value: match[0]};
            }
            return null;
        }

        function tokenizeString(chars) {
            if (chars[0] === '"') {
                const startChar = chars.shift();
                const letters = [startChar];
                while (chars[0] && (chars[0] !== startChar || letters[letters.length - 1] === "\\")) {
                    letters.push(chars.shift());
                }
                if (chars[0] === '"') {
                    letters.push(chars.shift());
                }
                return {
                    type: "STRING",
                    value: letters.join(""),
                };
            }
            return null;
        }

        function tokenizeSymbol(chars) {
            const result = [];
            // there are two main cases to manage: either something which starts with
            // a ', like 'Sheet 2'A2, or a word-like element.
            if (chars[0] === "'") {
                let lastChar = chars.shift();
                result.push(lastChar);
                while (chars[0]) {
                    lastChar = chars.shift();
                    result.push(lastChar);
                    if (lastChar === "'") {
                        if (chars[0] && chars[0] === "'") {
                            lastChar = chars.shift();
                            result.push(lastChar);
                        } else {
                            break;
                        }
                    }
                }
                if (lastChar !== "'") {
                    return {
                        type: "UNKNOWN",
                        value: result.join(""),
                    };
                }
            }
            while (chars[0] && chars[0].match(separatorRegexp)) {
                result.push(chars.shift());
            }
            if (result.length) {
                const value = result.join("");
                const isFunction = value.toUpperCase() in functions$1;
                const type = isFunction ? "FUNCTION" : "SYMBOL";
                return {type, value};
            }
            return null;
        }

        function enrichTokens(tokens) {
            let current = 0;
            return tokens.map((x) => {
                const len = x.value.toString().length;
                const token = Object.assign({}, x, {
                    start: current,
                    end: current + len,
                    length: len,
                });
                current = token.end;
                return token;
            });
        }

        function mergeSymbolsIntoRanges(result, removeSpace = false) {
            let operator = undefined;
            let refStart = undefined;
            let refEnd = undefined;
            let startIncludingSpaces = undefined;
            const reset = () => {
                startIncludingSpaces = undefined;
                refStart = undefined;
                operator = undefined;
                refEnd = undefined;
            };
            for (let i = 0; i < result.length; i++) {
                const token = result[i];
                if (startIncludingSpaces) {
                    if (refStart) {
                        if (token.type === "SPACE") {
                            continue;
                        } else if (token.type === "OPERATOR" && token.value === ":") {
                            operator = i;
                        } else if (operator && token.type === "SYMBOL") {
                            refEnd = i;
                        } else {
                            if (startIncludingSpaces && refStart && operator && refEnd) {
                                const newToken = {
                                    type: "SYMBOL",
                                    start: result[startIncludingSpaces].start,
                                    end: result[i - 1].end,
                                    length: result[i - 1].end - result[startIncludingSpaces].start,
                                    value: result
                                        .slice(startIncludingSpaces, i)
                                        .filter((x) => !removeSpace || x.type !== "SPACE")
                                        .map((x) => x.value)
                                        .join(""),
                                };
                                result.splice(startIncludingSpaces, i - startIncludingSpaces, newToken);
                                i = startIncludingSpaces + 1;
                                reset();
                            } else {
                                if (token.type === "SYMBOL") {
                                    startIncludingSpaces = i;
                                    refStart = i;
                                    operator = undefined;
                                } else {
                                    reset();
                                }
                            }
                        }
                    } else {
                        if (token.type === "SYMBOL") {
                            refStart = i;
                            operator = refEnd = undefined;
                        } else {
                            reset();
                        }
                    }
                } else {
                    if (["SPACE", "SYMBOL"].includes(token.type)) {
                        startIncludingSpaces = i;
                        refStart = token.type === "SYMBOL" ? i : undefined;
                        operator = refEnd = undefined;
                    } else {
                        reset();
                    }
                }
            }
            const i = result.length - 1;
            if (startIncludingSpaces && refStart && operator && refEnd) {
                const newToken = {
                    type: "SYMBOL",
                    start: result[startIncludingSpaces].start,
                    end: result[i].end,
                    length: result[i].end - result[startIncludingSpaces].start,
                    value: result
                        .slice(startIncludingSpaces, i + 1)
                        .filter((x) => !removeSpace || x.type !== "SPACE")
                        .map((x) => x.value)
                        .join(""),
                };
                result.splice(startIncludingSpaces, i - startIncludingSpaces + 1, newToken);
            }
            return result;
        }

        function toSimpleTokens(composerTokens) {
            return composerTokens.map((x) => {
                return {
                    type: x.type,
                    value: x.value,
                };
            });
        }

        function mapParenthesis(tokens) {
            let maxParen = 1;
            const stack = [];
            return tokens.map((token) => {
                if (token.type === "LEFT_PAREN") {
                    stack.push(maxParen);
                    token.parenIndex = maxParen;
                    maxParen++;
                } else if (token.type === "RIGHT_PAREN") {
                    token.parenIndex = stack.pop();
                }
                return token;
            });
        }

        function getComposerSheetName(sheetName) {
            if (sheetName.includes(" ")) {
                sheetName = `'${sheetName}'`;
            }
            return sheetName;
        }

        return {
            parseNumber,
            parseDateTime,
            formatDateTime,
            compile,
            isNumber,
            _lt,
            _parse,
            _tokenize,
            RefError,
            enrichTokens,
            mergeSymbolsIntoRanges,
            toSimpleTokens,
            cellReference,
            rangeReference,
            tokenColor,
            MatchingParenColor,
            colors,
            mapParenthesis,
            getComposerSheetName
        };
    }
);
