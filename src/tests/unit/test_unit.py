from __future__ import annotations

from typing import TYPE_CHECKING

# isort: off
from klegv8.build import semantics

# isort: on
import pytest
from pyk.kllvm.convert import llvm_to_pattern, pattern_to_llvm
from pyk.kore.match import kore_int
from pyk.prelude.kint import INT, intToken

from klegv8 import term_builder
from klegv8.term_builder import register
from klegv8.term_manip import kore_sparse_bytes, normalize_memory

if TYPE_CHECKING:
    from typing import Final

    from pyk.kast.inner import KInner, KSort
    from pyk.kore.syntax import Pattern

    from klegv8.tools import Tools


def _eval_call(tools: Tools, call: KInner, sort: KSort) -> KInner:
    return tools.krun.kore_to_kast(_eval_call_to_kore(tools, call, sort))


def _eval_call_to_kore(tools: Tools, call: KInner, sort: KSort) -> Pattern:
    llvm_input = pattern_to_llvm(tools.krun.kast_to_kore(call, sort))
    llvm_res = tools.runtime.evaluate(llvm_input)
    return llvm_to_pattern(llvm_res)


# test id, instruction binary as a string of 0s/1s, disassembled instruction
DISASS_TEST_DATA: Final[tuple[tuple[str, str, KInner], ...]] = (
    (
        'ADD x0, x0, x0',
        '10001011000000000000000000000000',
        term_builder.add_instr(register(0), register(0), register(0)),
    ),
    (
        'ADD x1, x0, x0',
        '10001011000000000000000000000001',
        term_builder.add_instr(register(1), register(0), register(0)),
    ),
    (
        'AND x0, x0, x0',
        '10001010000000000000000000000000',
        term_builder.and_instr(register(0), register(0), register(0)),
    ),
    (
        'AND x0, x0, x0',
        '10001010000000010000000000000000',
        term_builder.and_instr(register(0), register(0), register(1)),
    ),
    (
        'SDIV x0, x0, x0',
        '10011010110000000000100000000000',
        term_builder.sdiv_instr(register(0), register(0), register(0)),
    ),
    (
        'UDIV x0, x0, x0',
        '10011010110000000000110000000000',
        term_builder.udiv_instr(register(0), register(0), register(0)),
    ),
    (
        'ADDI x0, x0, #15',
        '10010001000000000011110000000000',
        term_builder.addi_instr(register(0), register(0), intToken(15)),
    ),
)

@pytest.mark.parametrize(
    'instr_bits,expected',
    [(instr_bits, expected) for (_, instr_bits, expected) in DISASS_TEST_DATA],
    ids=[test_id for test_id, *_ in DISASS_TEST_DATA],
)
def test_disassemble(instr_bits: str, expected: KInner) -> None:
    assert len(instr_bits) == 32
    tools = semantics()
    disass_call = term_builder.disassemble(intToken(int(instr_bits, 2)))
    actual = _eval_call(tools, disass_call, term_builder.sort_instruction())
    assert actual == expected


# test id, initial memory, addr to write, byte to write
MEMORY_TEST_DATA: Final[tuple[tuple[str, dict[int, bytes], int, int], ...]] = (
    ('empty_start', {}, 0, 0x1A),
    ('empty_later', {}, 10, 0x1A),
    ('mid_bytes', {1: b'\x7F\x7F'}, 2, 0x1A),
    ('start_pre_bytes', {1: b'\x7F\x7F'}, 0, 0x1A),
    ('empty_pre_bytes', {2: b'\x7F\x7F'}, 1, 0x1A),
    ('end_post_bytes', {2: b'\x7F\x7F'}, 4, 0x1A),
    ('empty_post_bytes', {2: b'\x7F\x7F', 6: b'\x7F'}, 4, 0x1A),
    ('end', {2: b'\x7F\x7F'}, 5, 0x1A),
    ('merge_bytes', {1: b'\x7F\x7F', 4: b'\x7F'}, 3, 0x1A),
)


@pytest.mark.parametrize(
    'memory,addr,byte',
    [(memory, addr, byte) for (_, memory, addr, byte) in MEMORY_TEST_DATA],
    ids=[test_id for test_id, *_ in MEMORY_TEST_DATA],
)
def test_memory(memory: dict[int, bytes], addr: int, byte: int) -> None:
    assert 0 <= byte <= 0xFF
    for val in memory.values():
        for byte in val:
            assert 0 <= byte <= 0xFF

    byte_val = byte.to_bytes(1, 'big')

    # Manually compute the expected final memory state
    memory_expect: dict[int, bytes] = {}
    stored = False
    for start, val in memory.items():
        if start <= addr and addr < start + len(val):
            val_idx = addr - start
            memory_expect[start] = val[:val_idx] + byte_val + val[val_idx + 1 :]
            stored = True
        else:
            memory_expect[start] = val
    if not stored:
        memory_expect[addr] = byte_val
    memory_expect = normalize_memory(memory_expect)

    # Execute storeByte to get the actual final memory state
    tools = semantics()
    memory_sb = term_builder.sparse_bytes(memory)
    addr_word = term_builder.word(addr)

    store_call = term_builder.store_byte(memory_sb, addr_word, intToken(byte))
    memory_actual_sb_kore = _eval_call_to_kore(tools, store_call, term_builder.sort_memory())
    memory_actual = kore_sparse_bytes(memory_actual_sb_kore)

    assert memory_actual == memory_expect

    # Also execute loadByte and check that we correctly read back the written value
    memory_actual_sb = tools.krun.kore_to_kast(memory_actual_sb_kore)
    load_call = term_builder.load_byte(memory_actual_sb, addr_word)
    load_actual = kore_int(_eval_call_to_kore(tools, load_call, INT))

    assert load_actual == byte
