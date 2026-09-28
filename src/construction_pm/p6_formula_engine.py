from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import Mapping


class FormulaError(ValueError):
    """Base error for safe, deterministic formula compilation/evaluation."""


class FormulaSyntaxError(FormulaError):
    """Raised when a formula cannot be parsed."""


class FormulaTypeError(FormulaError):
    """Raised when formula operands or the declared result type are incompatible."""


class FormulaDependencyError(FormulaError):
    """Raised when formula dependencies are missing or cyclic."""


class FormulaType(str, Enum):
    NULL = "null"
    BOOLEAN = "boolean"
    NUMBER = "number"
    TEXT = "text"
    DATE = "date"
    DATETIME = "datetime"


@dataclass(frozen=True)
class FormulaValue:
    type: FormulaType
    value: object
    unit: str | None = None

    @staticmethod
    def null() -> "FormulaValue":
        return FormulaValue(FormulaType.NULL, None)

    @staticmethod
    def boolean(value: bool) -> "FormulaValue":
        if not isinstance(value, bool):
            raise FormulaTypeError("BOOLEAN_VALUE_REQUIRED")
        return FormulaValue(FormulaType.BOOLEAN, value)

    @staticmethod
    def number(value: Decimal | int | str, unit: str | None = None) -> "FormulaValue":
        try:
            decimal_value = value if isinstance(value, Decimal) else Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise FormulaTypeError("NUMBER_VALUE_REQUIRED") from exc
        if not decimal_value.is_finite():
            raise FormulaTypeError("FINITE_NUMBER_REQUIRED")
        if unit is not None and (not isinstance(unit, str) or not unit.strip()):
            raise FormulaTypeError("INVALID_UNIT")
        return FormulaValue(FormulaType.NUMBER, decimal_value, unit)

    @staticmethod
    def text(value: str) -> "FormulaValue":
        if not isinstance(value, str):
            raise FormulaTypeError("TEXT_VALUE_REQUIRED")
        return FormulaValue(FormulaType.TEXT, value)

    @staticmethod
    def date(value: date) -> "FormulaValue":
        if isinstance(value, datetime) or not isinstance(value, date):
            raise FormulaTypeError("DATE_VALUE_REQUIRED")
        return FormulaValue(FormulaType.DATE, value)

    @staticmethod
    def datetime(value: datetime) -> "FormulaValue":
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise FormulaTypeError("TIMEZONE_AWARE_DATETIME_REQUIRED")
        return FormulaValue(FormulaType.DATETIME, value)

    def require_number(self) -> Decimal:
        if self.type is not FormulaType.NUMBER:
            raise FormulaTypeError("NUMBER_OPERAND_REQUIRED")
        return self.value  # type: ignore[return-value]

    def require_boolean(self) -> bool:
        if self.type is not FormulaType.BOOLEAN:
            raise FormulaTypeError("BOOLEAN_OPERAND_REQUIRED")
        return self.value  # type: ignore[return-value]


class TokenKind(str, Enum):
    NUMBER = "NUMBER"
    STRING = "STRING"
    FIELD = "FIELD"
    IDENT = "IDENT"
    OP = "OP"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    COMMA = "COMMA"
    EOF = "EOF"


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    value: str
    position: int


def tokenize(expression: str) -> tuple[Token, ...]:
    if not isinstance(expression, str) or not expression.strip():
        raise FormulaSyntaxError("EMPTY_FORMULA")

    tokens: list[Token] = []
    i = 0
    length = len(expression)

    while i < length:
        char = expression[i]
        if char.isspace():
            i += 1
            continue

        if char in "[]":
            if char == "]":
                raise FormulaSyntaxError(f"UNEXPECTED_TOKEN_AT_{i}")
            end = expression.find("]", i + 1)
            if end < 0:
                raise FormulaSyntaxError("UNTERMINATED_FIELD_REFERENCE")
            field_id = expression[i + 1 : end].strip()
            if not field_id:
                raise FormulaSyntaxError("EMPTY_FIELD_REFERENCE")
            tokens.append(Token(TokenKind.FIELD, field_id, i))
            i = end + 1
            continue

        if char in "'\"":
            quote = char
            start = i
            i += 1
            value: list[str] = []
            while i < length:
                if expression[i] == quote:
                    if i + 1 < length and expression[i + 1] == quote:
                        value.append(quote)
                        i += 2
                        continue
                    break
                value.append(expression[i])
                i += 1
            if i >= length or expression[i] != quote:
                raise FormulaSyntaxError(f"UNTERMINATED_STRING_AT_{start}")
            tokens.append(Token(TokenKind.STRING, "".join(value), start))
            i += 1
            continue

        if char.isdigit() or (char == "." and i + 1 < length and expression[i + 1].isdigit()):
            start = i
            dot_seen = False
            i += 1
            while i < length:
                current = expression[i]
                if current.isdigit():
                    i += 1
                    continue
                if current == "." and not dot_seen:
                    dot_seen = True
                    i += 1
                    continue
                break
            tokens.append(Token(TokenKind.NUMBER, expression[start:i], start))
            continue

        if char.isalpha() or char == "_":
            start = i
            i += 1
            while i < length and (expression[i].isalnum() or expression[i] in "._"):
                i += 1
            tokens.append(Token(TokenKind.IDENT, expression[start:i], start))
            continue

        two = expression[i : i + 2]
        if two in {"<=", ">=", "<>", "!=", "==", "&&", "||"}:
            tokens.append(Token(TokenKind.OP, two, i))
            i += 2
            continue

        if char in "+-*/^=<>&|":
            tokens.append(Token(TokenKind.OP, char, i))
            i += 1
            continue
        if char == "(":
            tokens.append(Token(TokenKind.LPAREN, char, i))
            i += 1
            continue
        if char == ")":
            tokens.append(Token(TokenKind.RPAREN, char, i))
            i += 1
            continue
        if char == ",":
            tokens.append(Token(TokenKind.COMMA, char, i))
            i += 1
            continue

        raise FormulaSyntaxError(f"UNSUPPORTED_TOKEN_AT_{i}")

    tokens.append(Token(TokenKind.EOF, "", length))
    return tuple(tokens)


@dataclass(frozen=True)
class LiteralNode:
    value: FormulaValue


@dataclass(frozen=True)
class FieldNode:
    field_id: str


@dataclass(frozen=True)
class UnaryNode:
    operator: str
    operand: "ExpressionNode"


@dataclass(frozen=True)
class BinaryNode:
    operator: str
    left: "ExpressionNode"
    right: "ExpressionNode"


@dataclass(frozen=True)
class FunctionNode:
    name: str
    arguments: tuple["ExpressionNode", ...]


ExpressionNode = LiteralNode | FieldNode | UnaryNode | BinaryNode | FunctionNode


class _Parser:
    def __init__(self, tokens: tuple[Token, ...]) -> None:
        self.tokens = tokens
        self.index = 0

    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def advance(self) -> Token:
        token = self.current
        self.index += 1
        return token

    def expect(self, kind: TokenKind, value: str | None = None) -> Token:
        token = self.current
        if token.kind is not kind or (value is not None and token.value.upper() != value.upper()):
            expected = value or kind.value
            raise FormulaSyntaxError(f"EXPECTED_{expected}_AT_{token.position}")
        return self.advance()

    def parse(self) -> ExpressionNode:
        result = self.parse_or()
        self.expect(TokenKind.EOF)
        return result

    def parse_or(self) -> ExpressionNode:
        node = self.parse_and()
        while self._match_operator("OR") or self._match_operator("||"):
            node = BinaryNode("OR", node, self.parse_and())
        return node

    def parse_and(self) -> ExpressionNode:
        node = self.parse_comparison()
        while self._match_operator("AND") or self._match_operator("&&"):
            node = BinaryNode("AND", node, self.parse_comparison())
        return node

    def parse_comparison(self) -> ExpressionNode:
        node = self.parse_additive()
        while self.current.kind is TokenKind.OP and self.current.value in {"=", "==", "!=", "<>", "<", "<=", ">", ">="}:
            operator = self.advance().value
            node = BinaryNode(operator, node, self.parse_additive())
        return node

    def parse_additive(self) -> ExpressionNode:
        node = self.parse_multiplicative()
        while self.current.kind is TokenKind.OP and self.current.value in {"+", "-"}:
            operator = self.advance().value
            node = BinaryNode(operator, node, self.parse_multiplicative())
        return node

    def parse_multiplicative(self) -> ExpressionNode:
        node = self.parse_power()
        while self.current.kind is TokenKind.OP and self.current.value in {"*", "/"}:
            operator = self.advance().value
            node = BinaryNode(operator, node, self.parse_power())
        return node

    def parse_power(self) -> ExpressionNode:
        node = self.parse_unary()
        if self.current.kind is TokenKind.OP and self.current.value == "^":
            self.advance()
            node = BinaryNode("^", node, self.parse_power())
        return node

    def parse_unary(self) -> ExpressionNode:
        if self.current.kind is TokenKind.OP and self.current.value in {"+", "-"}:
            return UnaryNode(self.advance().value, self.parse_unary())
        if self._match_operator("NOT") or self._match_operator("!"):
            return UnaryNode("NOT", self.parse_unary())
        return self.parse_primary()

    def parse_primary(self) -> ExpressionNode:
        token = self.current
        if token.kind is TokenKind.NUMBER:
            self.advance()
            try:
                return LiteralNode(FormulaValue.number(Decimal(token.value)))
            except (InvalidOperation, FormulaError) as exc:
                raise FormulaSyntaxError("INVALID_NUMBER_LITERAL") from exc

        if token.kind is TokenKind.STRING:
            self.advance()
            return LiteralNode(FormulaValue.text(token.value))

        if token.kind is TokenKind.FIELD:
            self.advance()
            return FieldNode(token.value)

        if token.kind is TokenKind.IDENT:
            name = self.advance().value
            upper = name.upper()
            if upper == "TRUE":
                return LiteralNode(FormulaValue.boolean(True))
            if upper == "FALSE":
                return LiteralNode(FormulaValue.boolean(False))
            if upper == "NULL":
                return LiteralNode(FormulaValue.null())
            if self.current.kind is TokenKind.LPAREN:
                self.advance()
                arguments: list[ExpressionNode] = []
                if self.current.kind is not TokenKind.RPAREN:
                    while True:
                        arguments.append(self.parse_or())
                        if self.current.kind is not TokenKind.COMMA:
                            break
                        self.advance()
                self.expect(TokenKind.RPAREN)
                return FunctionNode(upper, tuple(arguments))
            raise FormulaSyntaxError(f"BARE_IDENTIFIER_NOT_ALLOWED_{name}")

        if token.kind is TokenKind.LPAREN:
            self.advance()
            node = self.parse_or()
            self.expect(TokenKind.RPAREN)
            return node

        raise FormulaSyntaxError(f"EXPECTED_EXPRESSION_AT_{token.position}")

    def _match_operator(self, expected: str) -> bool:
        if self.current.kind is TokenKind.IDENT and self.current.value.upper() == expected.upper():
            self.advance()
            return True
        if self.current.kind is TokenKind.OP and self.current.value == expected:
            self.advance()
            return True
        return False


@dataclass(frozen=True)
class FormulaSchemaValue:
    type: FormulaType
    unit: str | None = None


@dataclass(frozen=True)
class FormulaDefinition:
    formula_id: str
    version: str
    expression: str
    result_type: FormulaType

    def validate(self) -> None:
        if not self.formula_id.strip():
            raise FormulaError("INVALID_FORMULA_ID")
        if not self.version.strip():
            raise FormulaError("INVALID_FORMULA_VERSION")


@dataclass(frozen=True)
class CompiledFormula:
    definition: FormulaDefinition
    ast: ExpressionNode
    inferred_type: FormulaType
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class _TypeInfo:
    type: FormulaType
    unit: str | None = None


def parse_formula(expression: str) -> ExpressionNode:
    return _Parser(tokenize(expression)).parse()


def analyze_dependencies(ast: ExpressionNode) -> tuple[str, ...]:
    dependencies: set[str] = set()

    def walk(node: ExpressionNode) -> None:
        if isinstance(node, FieldNode):
            dependencies.add(node.field_id)
        elif isinstance(node, UnaryNode):
            walk(node.operand)
        elif isinstance(node, BinaryNode):
            walk(node.left)
            walk(node.right)
        elif isinstance(node, FunctionNode):
            for argument in node.arguments:
                walk(argument)

    walk(ast)
    return tuple(sorted(dependencies))


def _require_same_numeric_unit(left: _TypeInfo, right: _TypeInfo) -> str | None:
    if left.unit and right.unit and left.unit != right.unit:
        raise FormulaTypeError("INCOMPATIBLE_UNITS")
    return left.unit or right.unit


def _infer(node: ExpressionNode, schema: Mapping[str, FormulaSchemaValue]) -> _TypeInfo:
    if isinstance(node, LiteralNode):
        return _TypeInfo(node.value.type, node.value.unit)

    if isinstance(node, FieldNode):
        try:
            return _TypeInfo(schema[node.field_id].type, schema[node.field_id].unit)
        except KeyError as exc:
            raise FormulaDependencyError(f"FIELD_NOT_FOUND:{node.field_id}") from exc

    if isinstance(node, UnaryNode):
        operand = _infer(node.operand, schema)
        if node.operator in {"+", "-"}:
            if operand.type is not FormulaType.NUMBER:
                raise FormulaTypeError("UNARY_NUMBER_REQUIRED")
            return operand
        if node.operator == "NOT":
            if operand.type is not FormulaType.BOOLEAN:
                raise FormulaTypeError("UNARY_BOOLEAN_REQUIRED")
            return _TypeInfo(FormulaType.BOOLEAN)
        raise FormulaTypeError("UNSUPPORTED_UNARY_OPERATOR")

    if isinstance(node, BinaryNode):
        left = _infer(node.left, schema)
        right = _infer(node.right, schema)
        if node.operator in {"+", "-", "*", "/", "^"}:
            if left.type is FormulaType.NULL:
                if right.type is not FormulaType.NUMBER:
                    raise FormulaTypeError("NUMERIC_OPERANDS_REQUIRED")
                return right
            if right.type is FormulaType.NULL:
                if left.type is not FormulaType.NUMBER:
                    raise FormulaTypeError("NUMERIC_OPERANDS_REQUIRED")
                return left
            if left.type is not FormulaType.NUMBER or right.type is not FormulaType.NUMBER:
                raise FormulaTypeError("NUMERIC_OPERANDS_REQUIRED")
            if node.operator in {"+", "-"}:
                unit = _require_same_numeric_unit(left, right)
            elif node.operator == "^":
                if right.unit is not None:
                    raise FormulaTypeError("POWER_EXPONENT_MUST_BE_UNITLESS")
                unit = left.unit
            else:
                if left.unit and right.unit:
                    raise FormulaTypeError("COMPOSITE_UNIT_NOT_SUPPORTED")
                unit = left.unit or (None if node.operator == "/" else right.unit)
            return _TypeInfo(FormulaType.NUMBER, unit)

        if node.operator in {"AND", "OR"}:
            if left.type is not FormulaType.NULL and left.type is not FormulaType.BOOLEAN:
                raise FormulaTypeError("BOOLEAN_OPERANDS_REQUIRED")
            if right.type is not FormulaType.NULL and right.type is not FormulaType.BOOLEAN:
                raise FormulaTypeError("BOOLEAN_OPERANDS_REQUIRED")
            return _TypeInfo(FormulaType.BOOLEAN)

        if node.operator in {"=", "==", "!=", "<>", "<", "<=", ">", ">="}:
            compatible = (
                left.type is right.type
                or (left.type is FormulaType.NUMBER and right.type is FormulaType.NUMBER)
                or left.type is FormulaType.NULL
                or right.type is FormulaType.NULL
            )
            if not compatible:
                raise FormulaTypeError("INCOMPATIBLE_COMPARISON_TYPES")
            if left.type is FormulaType.NUMBER and right.type is FormulaType.NUMBER:
                _require_same_numeric_unit(left, right)
            return _TypeInfo(FormulaType.BOOLEAN)

        raise FormulaTypeError("UNSUPPORTED_BINARY_OPERATOR")

    if isinstance(node, FunctionNode):
        args = [_infer(argument, schema) for argument in node.arguments]
        name = node.name
        if name == "IF":
            if len(args) != 3 or args[0].type is not FormulaType.BOOLEAN:
                raise FormulaTypeError("IF_REQUIRES_BOOLEAN_CONDITION_AND_TWO_BRANCHES")
            if args[1].type is FormulaType.NULL:
                return args[2]
            if args[2].type is FormulaType.NULL:
                return args[1]
            if args[1].type is not args[2].type:
                raise FormulaTypeError("IF_BRANCH_TYPES_MUST_MATCH")
            if args[1].type is FormulaType.NUMBER:
                unit = _require_same_numeric_unit(args[1], args[2])
                return _TypeInfo(FormulaType.NUMBER, unit)
            return args[1]
        if name in {"SUM", "MIN", "MAX"}:
            numeric_args = [item for item in args if item.type is not FormulaType.NULL]
            if not args or any(item.type is not FormulaType.NUMBER for item in numeric_args):
                raise FormulaTypeError(f"{name}_REQUIRES_NUMBERS")
            if not numeric_args:
                return _TypeInfo(FormulaType.NUMBER)
            unit = numeric_args[0].unit
            for item in numeric_args[1:]:
                unit = _require_same_numeric_unit(_TypeInfo(FormulaType.NUMBER, unit), item)
            return _TypeInfo(FormulaType.NUMBER, unit)
        if name == "ABS":
            if len(args) != 1 or args[0].type is not FormulaType.NUMBER:
                raise FormulaTypeError("ABS_REQUIRES_ONE_NUMBER")
            return args[0]
        if name == "ROUND":
            if len(args) not in {1, 2} or args[0].type is not FormulaType.NUMBER:
                raise FormulaTypeError("ROUND_REQUIRES_NUMBER_AND_OPTIONAL_DIGITS")
            if len(args) == 2 and args[1].type is not FormulaType.NUMBER:
                raise FormulaTypeError("ROUND_DIGITS_MUST_BE_NUMBER")
            return args[0]
        if name == "COALESCE":
            if not args:
                raise FormulaTypeError("COALESCE_REQUIRES_ARGUMENTS")
            non_null = [item for item in args if item.type is not FormulaType.NULL]
            if not non_null:
                return _TypeInfo(FormulaType.NULL)
            first = non_null[0]
            for item in non_null[1:]:
                if item.type is not first.type:
                    raise FormulaTypeError("COALESCE_TYPES_MUST_MATCH")
                if first.type is FormulaType.NUMBER:
                    _require_same_numeric_unit(first, item)
            return first
        if name == "NOT":
            if len(args) != 1 or args[0].type is not FormulaType.BOOLEAN:
                raise FormulaTypeError("NOT_REQUIRES_ONE_BOOLEAN")
            return _TypeInfo(FormulaType.BOOLEAN)
        if name in {"AND", "OR"}:
            if len(args) < 2 or any(item.type not in {FormulaType.BOOLEAN, FormulaType.NULL} for item in args):
                raise FormulaTypeError(f"{name}_REQUIRES_BOOLEAN_ARGUMENTS")
            return _TypeInfo(FormulaType.BOOLEAN)
        raise FormulaTypeError(f"UNSUPPORTED_FUNCTION:{name}")

    raise FormulaTypeError("UNKNOWN_AST_NODE")


def compile_formula(
    definition: FormulaDefinition,
    schema: Mapping[str, FormulaSchemaValue],
) -> CompiledFormula:
    definition.validate()
    ast = parse_formula(definition.expression)
    inferred = _infer(ast, schema)
    if inferred.type is not definition.result_type:
        raise FormulaTypeError(
            f"RESULT_TYPE_MISMATCH:{inferred.type.value}!={definition.result_type.value}"
        )
    return CompiledFormula(
        definition=definition,
        ast=ast,
        inferred_type=inferred.type,
        dependencies=analyze_dependencies(ast),
    )


def _evaluate(node: ExpressionNode, values: Mapping[str, FormulaValue]) -> FormulaValue:
    if isinstance(node, LiteralNode):
        return node.value

    if isinstance(node, FieldNode):
        try:
            return values[node.field_id]
        except KeyError as exc:
            raise FormulaDependencyError(f"VALUE_NOT_FOUND:{node.field_id}") from exc

    if isinstance(node, UnaryNode):
        operand = _evaluate(node.operand, values)
        if operand.type is FormulaType.NULL:
            return FormulaValue.null()
        if node.operator == "+":
            operand.require_number()
            return operand
        if node.operator == "-":
            return FormulaValue.number(-operand.require_number(), operand.unit)
        if node.operator == "NOT":
            return FormulaValue.boolean(not operand.require_boolean())
        raise FormulaTypeError("UNSUPPORTED_UNARY_OPERATOR")

    if isinstance(node, BinaryNode):
        left = _evaluate(node.left, values)
        right = _evaluate(node.right, values)
        operator = node.operator

        if operator == "AND":
            if left.type is FormulaType.BOOLEAN and not left.value:
                return FormulaValue.boolean(False)
            if right.type is FormulaType.BOOLEAN and not right.value:
                return FormulaValue.boolean(False)
            if left.type is FormulaType.NULL or right.type is FormulaType.NULL:
                return FormulaValue.null()
            return FormulaValue.boolean(True)

        if operator == "OR":
            if left.type is FormulaType.BOOLEAN and left.value:
                return FormulaValue.boolean(True)
            if right.type is FormulaType.BOOLEAN and right.value:
                return FormulaValue.boolean(True)
            if left.type is FormulaType.NULL or right.type is FormulaType.NULL:
                return FormulaValue.null()
            return FormulaValue.boolean(False)

        if operator in {"+", "-", "*", "/", "^"}:
            if left.type is FormulaType.NULL or right.type is FormulaType.NULL:
                return FormulaValue.null()
            a = left.require_number()
            b = right.require_number()
            if operator in {"+", "-"}:
                unit = _require_same_numeric_unit(
                    _TypeInfo(FormulaType.NUMBER, left.unit),
                    _TypeInfo(FormulaType.NUMBER, right.unit),
                )
            elif operator == "^":
                if right.unit is not None:
                    raise FormulaTypeError("POWER_EXPONENT_MUST_BE_UNITLESS")
                unit = left.unit
            else:
                if left.unit and right.unit:
                    raise FormulaTypeError("COMPOSITE_UNIT_NOT_SUPPORTED")
                unit = left.unit or (None if operator == "/" else right.unit)
            if operator == "+":
                return FormulaValue.number(a + b, unit)
            if operator == "-":
                return FormulaValue.number(a - b, unit)
            if operator == "*":
                return FormulaValue.number(a * b, unit)
            if operator == "/":
                if b == 0:
                    raise FormulaError("DIVISION_BY_ZERO")
                return FormulaValue.number(a / b, unit)
            return FormulaValue.number(a ** int(b), unit)

        if operator in {"=", "==", "!=", "<>", "<", "<=", ">", ">="}:
            if left.type is FormulaType.NULL or right.type is FormulaType.NULL:
                return FormulaValue.null()
            if left.type is FormulaType.NUMBER and right.type is FormulaType.NUMBER:
                _require_same_numeric_unit(
                    _TypeInfo(FormulaType.NUMBER, left.unit),
                    _TypeInfo(FormulaType.NUMBER, right.unit),
                )
            if left.type is not right.type:
                raise FormulaTypeError("INCOMPATIBLE_COMPARISON_TYPES")
            a, b = left.value, right.value
            result = {
                "=": a == b,
                "==": a == b,
                "!=": a != b,
                "<>": a != b,
                "<": a < b,
                "<=": a <= b,
                ">": a > b,
                ">=": a >= b,
            }[operator]
            return FormulaValue.boolean(result)

        raise FormulaTypeError("UNSUPPORTED_BINARY_OPERATOR")

    if isinstance(node, FunctionNode):
        args = [_evaluate(argument, values) for argument in node.arguments]
        name = node.name
        if name == "IF":
            condition = args[0]
            if condition.type is FormulaType.NULL:
                return FormulaValue.null()
            return args[1] if condition.require_boolean() else args[2]
        if name == "SUM":
            present = [item for item in args if item.type is not FormulaType.NULL]
            if not present:
                return FormulaValue.null()
            total = Decimal("0")
            unit: str | None = None
            for item in present:
                value = item.require_number()
                unit = _require_same_numeric_unit(
                    _TypeInfo(FormulaType.NUMBER, unit),
                    _TypeInfo(FormulaType.NUMBER, item.unit),
                )
                total += value
            return FormulaValue.number(total, unit)
        if name in {"MIN", "MAX"}:
            present = [item for item in args if item.type is not FormulaType.NULL]
            if not present:
                return FormulaValue.null()
            first = present[0]
            for item in present[1:]:
                _require_same_numeric_unit(
                    _TypeInfo(FormulaType.NUMBER, first.unit),
                    _TypeInfo(FormulaType.NUMBER, item.unit),
                )
            selected = min(present, key=lambda item: item.require_number()) if name == "MIN" else max(
                present, key=lambda item: item.require_number()
            )
            return selected
        if name == "ABS":
            item = args[0]
            if item.type is FormulaType.NULL:
                return FormulaValue.null()
            return FormulaValue.number(abs(item.require_number()), item.unit)
        if name == "ROUND":
            item = args[0]
            if item.type is FormulaType.NULL:
                return FormulaValue.null()
            digits = int(args[1].require_number()) if len(args) == 2 and args[1].type is not FormulaType.NULL else 0
            quantum = Decimal(1).scaleb(-digits)
            return FormulaValue.number(item.require_number().quantize(quantum, rounding=ROUND_HALF_UP), item.unit)
        if name == "COALESCE":
            for item in args:
                if item.type is not FormulaType.NULL:
                    return item
            return FormulaValue.null()
        if name == "NOT":
            item = args[0]
            if item.type is FormulaType.NULL:
                return FormulaValue.null()
            return FormulaValue.boolean(not item.require_boolean())
        if name == "AND":
            for item in args:
                if item.type is FormulaType.BOOLEAN and not item.value:
                    return FormulaValue.boolean(False)
                if item.type is FormulaType.NULL:
                    return FormulaValue.null()
            return FormulaValue.boolean(True)
        if name == "OR":
            for item in args:
                if item.type is FormulaType.BOOLEAN and item.value:
                    return FormulaValue.boolean(True)
                if item.type is FormulaType.NULL:
                    return FormulaValue.null()
            return FormulaValue.boolean(False)
        raise FormulaTypeError(f"UNSUPPORTED_FUNCTION:{name}")

    raise FormulaTypeError("UNKNOWN_AST_NODE")


def evaluate_formula(
    compiled: CompiledFormula,
    values: Mapping[str, FormulaValue],
) -> FormulaValue:
    result = _evaluate(compiled.ast, values)
    if result.type is FormulaType.NULL:
        return result
    if result.type is not compiled.definition.result_type:
        raise FormulaTypeError(
            f"EVALUATED_RESULT_TYPE_MISMATCH:{result.type.value}!={compiled.definition.result_type.value}"
        )
    return result


def detect_formula_cycles(formulas: Mapping[str, CompiledFormula]) -> None:
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(formula_id: str) -> None:
        status = state.get(formula_id, 0)
        if status == 1:
            cycle_start = stack.index(formula_id)
            cycle = " -> ".join(stack[cycle_start:] + [formula_id])
            raise FormulaDependencyError(f"CIRCULAR_DEPENDENCY:{cycle}")
        if status == 2:
            return

        if formula_id not in formulas:
            raise FormulaDependencyError(f"FORMULA_NOT_FOUND:{formula_id}")

        state[formula_id] = 1
        stack.append(formula_id)
        for dependency in formulas[formula_id].dependencies:
            if dependency in formulas:
                visit(dependency)
        stack.pop()
        state[formula_id] = 2

    for formula_id in sorted(formulas):
        visit(formula_id)


__all__ = [
    "CompiledFormula",
    "FormulaDefinition",
    "FormulaDependencyError",
    "FormulaError",
    "FormulaSchemaValue",
    "FormulaSyntaxError",
    "FormulaType",
    "FormulaTypeError",
    "FormulaValue",
    "analyze_dependencies",
    "compile_formula",
    "detect_formula_cycles",
    "evaluate_formula",
    "parse_formula",
    "tokenize",
]
