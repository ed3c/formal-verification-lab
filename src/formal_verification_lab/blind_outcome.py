"""Closed outcome parsing and allocation-free primary packets. No scoring."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


LABELS = frozenset('R0' + str(i) for i in range(1, 9))
IDS = tuple('Q' + str(i) for i in range(1, 9))
EVIDENCE_IDS = frozenset('G' + str(i) for i in range(1, 9))


class OutcomeError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(code + ': ' + message)


class ContractError(ValueError):
    pass


class PacketError(ValueError):
    pass


def _strict_json(raw):
    if type(raw) is not bytes:
        raise OutcomeError('RAW_TYPE', 'input must be bytes')
    try:
        text = raw.decode('utf-8', errors='strict')
    except UnicodeDecodeError as error:
        raise OutcomeError('UTF8', 'invalid UTF-8 at byte ' + str(error.start)) from error

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise OutcomeError('DUPLICATE_KEY', 'duplicate object key ' + repr(key))
            result[key] = value
        return result

    def constant(value):
        raise OutcomeError('NON_FINITE', 'JSON constant ' + value + ' is prohibited')

    def floating(value):
        result = float(value)
        if not math.isfinite(result):
            raise OutcomeError('NON_FINITE', 'non-finite numeric literal is prohibited')
        return result

    def integer(value):
        if len(value.lstrip('-')) > 16:
            raise OutcomeError('INTEGER_LITERAL_LIMIT', 'integer literal exceeds any closed outcome value')
        return int(value)

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant, parse_float=floating, parse_int=integer)
    except json.JSONDecodeError as error:
        raise OutcomeError('JSON_SYNTAX', 'invalid JSON at character ' + str(error.pos)) from error
    except RecursionError as error:
        raise OutcomeError('JSON_DEPTH', 'JSON nesting exceeds decoder depth') from error


def _spec(case, contract):
    if type(contract) is not dict or set(contract) != {'schema', 'artifact_keys', 'answer_keys', 'evidence_ids', 'cases'}:
        raise ContractError('contract fields must be schema/artifact_keys/answer_keys/evidence_ids/cases')
    if type(contract['schema']) is not int or contract['schema'] != 1:
        raise ContractError('contract schema must be integer 1')
    if contract['artifact_keys'] != ['schema', 'answers'] or contract['answer_keys'] != ['id', 'value', 'evidence']:
        raise ContractError('contract key declarations differ from the closed outcome shape')
    if type(contract['evidence_ids']) is not list or len(contract['evidence_ids']) != 8 or any(type(x) is not str for x in contract['evidence_ids']) or set(contract['evidence_ids']) != EVIDENCE_IDS:
        raise ContractError('contract evidence IDs must be G1 through G8')
    if type(case) is not str or type(contract['cases']) is not dict or case not in contract['cases']:
        raise ContractError('unknown case ' + repr(case))
    specs = contract['cases'][case]
    if type(specs) is not list or len(specs) != 8:
        raise ContractError('case must declare exactly eight value types')
    for value_type in specs:
        if value_type in ('integer', 'boolean'):
            continue
        if type(value_type) is not list or not value_type or any(type(x) is not str for x in value_type) or len(set(value_type)) != len(value_type):
            raise ContractError('unsupported value type in case ' + case)
    return specs


def validate(case, raw_bytes, contract):
    """Return a canonical artifact. Value validity is distinct from truth."""
    specs = _spec(case, contract)
    value = _strict_json(raw_bytes)
    if type(value) is not dict or set(value) != {'schema', 'answers'}:
        raise OutcomeError('TOP_KEYS', 'top object requires exactly schema and answers')
    if type(value['schema']) is not int or value['schema'] != 1:
        raise OutcomeError('SCHEMA_TYPE', 'schema must be integer 1, not bool or float')
    answers = value['answers']
    if type(answers) is not list or len(answers) != 8:
        raise OutcomeError('ANSWER_COUNT', 'answers must be an eight-element array')
    selected = {}
    for index, answer in enumerate(answers):
        location = 'answers[' + str(index) + ']'
        if type(answer) is not dict or set(answer) != {'id', 'value', 'evidence'}:
            raise OutcomeError('ANSWER_KEYS', location + ' requires exactly id/value/evidence')
        ident = answer['id']
        if type(ident) is not str or ident not in IDS:
            raise OutcomeError('ANSWER_ID', location + ' requires Q1 through Q8')
        if ident in selected:
            raise OutcomeError('DUPLICATE_ID', 'duplicate answer ID ' + ident)
        evidence = answer['evidence']
        if type(evidence) is not str or evidence not in EVIDENCE_IDS:
            raise OutcomeError('EVIDENCE_ID', ident + ' evidence must be one G1 through G8 string')
        declared = specs[int(ident[1:]) - 1]
        actual = answer['value']
        if declared == 'integer':
            valid = type(actual) is int and 0 <= actual <= 512
        elif declared == 'boolean':
            valid = type(actual) is bool
        else:
            valid = type(actual) is str and actual in declared
        if not valid:
            raise OutcomeError('VALUE_TYPE', ident + ' value does not match the declared closed type')
        selected[ident] = {'id': ident, 'value': actual, 'evidence': evidence}
    if set(selected) != set(IDS):
        raise OutcomeError('ANSWER_IDS', 'Q1 through Q8 must each occur once')
    return {'schema': 1, 'answers': [selected[ident] for ident in IDS]}


def canonical_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def build_primary_packet(entries, contract):
    """Accept only (neutral_label, case, raw_bytes) triples; return eight rows."""
    if type(entries) not in (list, tuple) or len(entries) != 8:
        raise PacketError('primary packet requires exactly eight entries')
    rows = {}
    for entry in entries:
        if type(entry) is not tuple or len(entry) != 3:
            raise PacketError('each entry must be exactly (label, case, raw_bytes), without metadata')
        label, case, raw = entry
        if type(label) is not str or label not in LABELS:
            raise PacketError('neutral labels must be R01 through R08')
        if type(raw) is not bytes:
            raise PacketError('entry raw_bytes must be bytes, without metadata')
        if label in rows:
            raise PacketError('duplicate neutral label ' + label)
        _spec(case, contract)
        try:
            artifact = validate(case, raw, contract)
        except OutcomeError:
            outcome = {'status': 'INVALID_OUTPUT', 'artifact': None}
        else:
            outcome = {'status': 'VALID_OUTPUT', 'artifact': artifact}
        rows[label] = {'label': label, 'case': case, 'outcome': outcome}
    if set(rows) != LABELS:
        raise PacketError('primary packet must have R01 through R08 once each')
    return {'schema': 1, 'rows': [rows[label] for label in sorted(LABELS)]}


def _read_contract(path):
    value = _strict_json(Path(path).read_bytes())
    if type(value) is not dict:
        raise ContractError('contract must be an object')
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='operation', required=True)
    check = commands.add_parser('validate')
    check.add_argument('--contract', required=True)
    check.add_argument('--case', required=True)
    check.add_argument('--input', required=True)
    packet = commands.add_parser('packet')
    packet.add_argument('--contract', required=True)
    packet.add_argument('--manifest', required=True)
    packet.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        contract = _read_contract(args.contract)
        if args.operation == 'validate':
            result = validate(args.case, Path(args.input).read_bytes(), contract)
            sys.stdout.buffer.write(canonical_bytes(result))
            return 0
        manifest = _strict_json(Path(args.manifest).read_bytes())
        if type(manifest) is not dict or set(manifest) != {'schema', 'entries'} or type(manifest['schema']) is not int or manifest['schema'] != 1 or type(manifest['entries']) is not list:
            raise PacketError('manifest requires only integer schema=1 and entries array')
        entries, ledger = [], []
        for entry in manifest['entries']:
            if type(entry) is not dict or set(entry) != {'label', 'case', 'path'} or type(entry['path']) is not str:
                raise PacketError('manifest entry requires only label/case/path')
            path = Path(entry['path'])
            if not path.is_absolute():
                path = Path(args.manifest).resolve().parent / path
            raw = path.read_bytes()
            entries.append((entry['label'], entry['case'], raw))
            ledger.append({'label': entry['label'], 'case': entry['case'], 'source': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'validation': None})
        primary = build_primary_packet(entries, contract)
        output = Path(args.output)
        output.mkdir(parents=False, exist_ok=False)
        raw_dir = output / 'raw'
        raw_dir.mkdir()
        for (label, case, raw), item in zip(entries, ledger):
            destination = raw_dir / (label + '.bin')
            destination.write_bytes(raw)
            destination.chmod(0o600)
            item['saved_raw'] = str(destination)
            try:
                validate(case, raw, contract)
            except OutcomeError as error:
                item['validation'] = {'status': 'INVALID_OUTPUT', 'error': str(error)}
            else:
                item['validation'] = {'status': 'VALID_OUTPUT', 'scoring': 'NOT_SCORED'}
        (output / 'primary.json').write_bytes(canonical_bytes(primary))
        (output / 'ledger.json').write_bytes(canonical_bytes({'schema': 1, 'entries': ledger}))
        return 0
    except (OutcomeError, ContractError, PacketError, OSError) as error:
        print(type(error).__name__ + ': ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
