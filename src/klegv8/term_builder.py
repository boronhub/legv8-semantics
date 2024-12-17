from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, cast

from pyk.kast.inner import KApply, KInner, KSort
from pyk.prelude.bytes import bytesToken
from pyk.prelude.kint import intToken

from klegv8.term_manip import normalize_memory

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import TypeVar

    T = TypeVar('T')


def halt_never() -> KInner:
    return KApply('HaltNever')


def halt_at_address(address: KInner) -> KInner:
    return KApply('HaltAtAddress', address)


def disassemble(instr: KInner) -> KInner:
    return KApply('disassemble', instr)


def sort_instruction() -> KSort:
    return KSort('Instruction')


def _reg_reg_imm_instr(reg_reg_imm_instr_name: KInner, reg1: KInner, reg2: KInner, imm: KInner) -> KInner:
    return KApply('RegRegImmInstr', reg_reg_imm_instr_name, reg1, reg2, imm)


def _reg_imm_instr(reg_imm_instr_name: KInner, reg: KInner, imm: KInner) -> KInner:
    return KApply('RegImmInstr', reg_imm_instr_name, reg, imm)


def _reg_reg_reg_instr(reg_reg_reg_instr_name: KInner, reg1: KInner, reg2: KInner, reg3: KInner) -> KInner:
    return KApply('RegRegRegInstr', reg_reg_reg_instr_name, reg1, reg2, reg3)


def _reg_imm_reg_instr(reg_imm_reg_instr_name: KInner, reg1: KInner, imm: KInner, reg2: KInner) -> KInner:
    return KApply('RegImmRegInstr', reg_imm_reg_instr_name, reg1, imm, reg2)


def register(num: int) -> KInner:
    return intToken(num)


def add_instr(rd: KInner, rn: KInner, rm: KInner) -> KInner:
    return _reg_reg_reg_instr(KApply('ADD'), rd, rn, rm)

def and_instr(rd: KInner, rn: KInner, rm: KInner) -> KInner:
    return _reg_reg_reg_instr(KApply('AND'), rd, rn, rm)

def sdiv_instr(rd: KInner, rn: KInner, rm: KInner) -> KInner:
    return _reg_reg_reg_instr(KApply('SDIV'), rd, rn, rm)

def udiv_instr(rd: KInner, rn: KInner, rm: KInner) -> KInner:
    return _reg_reg_reg_instr(KApply('UDIV'), rd, rn, rm)

def addi_instr(rd: KInner, rn: KInner, imm: KInner) -> KInner:
    return _reg_reg_imm_instr(KApply('ADDI'), rd, rn, imm)

def invalid_instr() -> KInner:
    return KApply('INVALID_INSTR')


def word(bits: KInner | int | str | bytes) -> KInner:
    match bits:
        case KInner():
            val = bits
        case int():
            assert bits >= 0
            val = intToken(bits)
        case str():
            val = intToken(int(bits, 2))
        case bytes():
            val = intToken(int.from_bytes(bits, 'big', signed=False))
    return KApply('W', val)


def dot_sb() -> KInner:
    return KApply('.SparseBytes')


def sb_empty(count: KInner) -> KInner:
    return KApply('SparseBytes:#empty', count)


def sb_bytes(bs: KInner) -> KInner:
    return KApply('SparseBytes:#bytes', bs)


def sb_empty_cons(empty: KInner, rest_bf: KInner) -> KInner:
    return KApply('SparseBytes:EmptyCons', empty, rest_bf)


def sb_bytes_cons(bs: KInner, rest_ef: KInner) -> KInner:
    return KApply('SparseBytes:BytesCons', bs, rest_ef)


def sparse_bytes(data: dict[int, bytes]) -> KInner:
    clean_data: list[tuple[int, bytes]] = sorted(normalize_memory(data).items())

    if len(clean_data) == 0:
        return dot_sb()

    # Collect all empty gaps between segements
    gaps = []
    start = clean_data[0][0]
    if start != 0:
        gaps.append((0, start))
    for (start1, val1), (start2, _) in itertools.pairwise(clean_data):
        end1 = start1 + len(val1)
        # normalize_memory should already have merged consecutive segments
        assert end1 < start2
        gaps.append((end1, start2 - end1))

    # Merge segments and gaps into a list of sparse bytes items
    sparse_data: list[tuple[int, int | bytes]] = sorted(
        cast('list[tuple[int, int | bytes]]', clean_data) + cast('list[tuple[int, int | bytes]]', gaps), reverse=True
    )

    sparse_k = dot_sb()
    for _, gap_or_val in sparse_data:
        if isinstance(gap_or_val, int):
            sparse_k = sb_empty_cons(sb_empty(intToken(gap_or_val)), sparse_k)
        elif isinstance(gap_or_val, bytes):
            sparse_k = sb_bytes_cons(sb_bytes(bytesToken(gap_or_val)), sparse_k)
        else:
            raise AssertionError()
    return sparse_k


def sort_memory() -> KSort:
    return KSort('SparseBytes')


def load_byte(mem: KInner, addr: KInner) -> KInner:
    return KApply('Memory:loadByte', mem, addr)


def store_byte(mem: KInner, addr: KInner, value: KInner) -> KInner:
    return KApply('Memory:storeByte', mem, addr, value)
