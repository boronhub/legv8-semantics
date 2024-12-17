# LEGv8 Execution
## Configuration
The configuration is divided into two sections:
- `<legv8>`, containing the state of the abstract machine.
- `<test>`, containing any additional state needed to run tests.

The `<legv8>` section contain the following cells:
- `<instrs>`, a K-sequence denoting a pipeline of operations to be executed. Initially, we load the `#EXECUTE` operation, which indicates that instructions should be continually fetched and executed.
- `<regs>`, a map from each initialized `Register` to its current value.
- `<pc>`, the program counter register.
- `<mem>`, a map from initialized `Word` addresses to the byte stored at the address.

The `<test>` section currently contains on a single cell:
- `<haltCond>`, a value indicating under which conditions the program should be halted.
```k
requires "legv8-disassemble.md"
requires "legv8-instructions.md"
requires "sparse-bytes.md"
requires "word.md"

module LEGV8-CONFIGURATION
  imports BOOL
  imports INT
  imports MAP
  imports RANGEMAP
  imports SPARSE-BYTES
  imports WORD

  syntax KItem ::= "#EXECUTE"

  configuration
    <legv8>
      <instrs> #EXECUTE ~> .K </instrs>
      <regs> .Map </regs> // Map{Register, Word}
      <pc> $PC:Word </pc>
      <flags> .Map </flags> // Map{Flag, Bool}
      <mem> $MEM:SparseBytes </mem>
    </legv8>
    <test>
      <haltCond> $HALT:HaltCondition </haltCond>
    </test>

  syntax HaltCondition
endmodule
```

## Termination
LEGv8 does not provide a `halt` instruction or equivalent, instead relying on the surrounding environment, e.g., making a sys-call to exit with a particular exit code.
As we do not model the surrounding environment, for testing purposes we add our own custom halting mechanism denoted by a `HaltCondition` value.

This is done with three components:
- A `HaltCondition` value stored in the configuation indicating under which conditions we should halt.
- A `#CHECK_HALT` operation indicating that the halt condition should be checked.
- A `#HALT` operation which terminates the simulation by consuming all following operations in the pipeline without executing them.
```k
module LEGV8-TERMINATION
  imports LEGV8-CONFIGURATION
  imports BOOL
  imports INT

  syntax KItem ::=
      "#HALT"
    | "#CHECK_HALT"

  rule <instrs> #HALT ~> (_ => .K) ...</instrs>

  syntax HaltCondition ::=
      "NEVER"                [symbol(HaltNever)]
    | "ADDRESS" "(" Word ")" [symbol(HaltAtAddress)]
```
The `NEVER` condition indicates that we should never halt.
```k
  rule <instrs> #CHECK_HALT => .K ...</instrs>
       <haltCond> NEVER </haltCond>
```
The `ADDRESS(_)` condition indicates that we should halt if the `PC` reaches a particular address.
```k
  rule <instrs> #CHECK_HALT => #HALT ...</instrs>
       <pc> PC </pc>
       <haltCond> ADDRESS(END) </haltCond>
       requires PC ==Word END

  rule <instrs> #CHECK_HALT => .K ...</instrs>
       <pc> PC </pc>
       <haltCond> ADDRESS(END) </haltCond>
       requires PC =/=Word END
endmodule
```

## Memory, Registers and Flags
LEGv8 uses a circular, byte-adressable memory space containing `2^XLEN` bytes.
```k
module LEGV8-MEMORY
  imports INT
  imports MAP
  imports RANGEMAP
  imports LEGV8-CONFIGURATION
  imports LEGV8-DISASSEMBLE
  imports LEGV8-INSTRUCTIONS
  imports WORD

  syntax Memory = SparseBytes
```
We abstract the particular memory representation behind `loadByte` and `storeByte` functions.
```k
  syntax Int ::= loadByte(memory: Memory, address: Word) [function, symbol(Memory:loadByte)]
  rule loadByte(MEM, W(ADDR)) => { readByte(MEM, ADDR) }:>Int

  syntax Memory ::= storeByte(memory: Memory, address: Word, byte: Int) [function, total, symbol(Memory:storeByte)]
  rule storeByte(MEM, W(ADDR), B) => writeByte(MEM, ADDR, B)
```
For multi-byte loads and stores, we presume a little-endian architecture.
```k
  syntax Int ::= loadBytes(memory: Memory, address: Word, numBytes: Int) [function]
  rule loadBytes(MEM, ADDR, 1  ) => loadByte(MEM, ADDR)
  rule loadBytes(MEM, ADDR, NUM) => (loadBytes(MEM, ADDR +Word W(1), NUM -Int 1) <<Int 8) |Int loadByte(MEM, ADDR) requires NUM >Int 1

  syntax Memory ::= storeBytes(memory: Memory, address: Word, bytes: Int, numBytes: Int) [function]
  rule storeBytes(MEM, ADDR, BS, 1  ) => storeByte(MEM, ADDR, BS)
  rule storeBytes(MEM, ADDR, BS, NUM) => storeBytes(storeByte(MEM, ADDR, BS &Int 255), ADDR +Word W(1), BS >>Int 8, NUM -Int 1) requires NUM >Int 1
```
Instructions are always 32-bits, and are stored in big-endian format regardless of the endianness of the overall architecture.
```k
  syntax Instruction ::= fetchInstr(memory: Memory, address: Word) [function]
  rule fetchInstr(MEM, ADDR) =>
      disassemble(loadByte(MEM, ADDR) |Int
                 (loadByte(MEM, ADDR +Word W(1)) <<Int 8 ) |Int
                 (loadByte(MEM, ADDR +Word W(2)) <<Int 16) |Int
                 (loadByte(MEM, ADDR +Word W(3)) <<Int 24)
                 )
      /* disassemble((loadByte(MEM, ADDR +Word W(3)) <<Int 24) |Int
                (loadByte(MEM, ADDR +Word W(2)) <<Int 16) |Int
                (loadByte(MEM, ADDR +Word W(1)) <<Int 8 ) |Int
                 loadByte(MEM, ADDR       )) */
```
Registers should be manipulated with the `writeReg` and `readReg` functions, which account for `x0` always being hard-wired to contain all `0`s.
```k
  syntax Map ::= writeReg(regs: Map, rd: Int, value: Word) [function]
  rule writeReg(REGS, 0 , _  ) => REGS
  rule writeReg(REGS, RD, VAL) => REGS[RD <- VAL] [owise]

  syntax Word ::= readReg(regs: Map, rs: Int) [function]
  rule readReg(_   , 0 ) => W(0)
  rule readReg(REGS, RS) => { REGS[RS] } :>Word [owise]
endmodule
```

## Instruction Execution
The `LEGV8` module contains the actual rules to fetch and execute instructions.
```k
module LEGV8
  imports LEGV8-CONFIGURATION
  imports LEGV8-DISASSEMBLE
  imports LEGV8-INSTRUCTIONS
  imports LEGV8-MEMORY
  imports LEGV8-TERMINATION
  imports WORD
```
`#EXECUTE` indicates that we should continuously fetch and execute instructions, loading the instruction into the `#NEXT[_]` operator.
```k
  syntax KItem ::= "#NEXT" "[" Instruction "]"

  rule <instrs> (.K => #NEXT[ fetchInstr(MEM, PC) ]) ~> #EXECUTE ...</instrs>
       <pc> PC </pc>
       <mem> MEM </mem>
```
`#NEXT[ I ]` sets up the pipeline to execute the the fetched instruction.
```k
  rule <instrs> #NEXT[ I ] => I ~> #PC[ I ] ~> #CHECK_HALT ...</instrs>
```
`#PC[ I ]` updates the `PC` as needed to fetch the next instruction after executing `I`. For most instructions, this increments `PC` by the width of the instruction (always `4` bytes in the base ISA). For branch and jump instructions, which already manually update the `PC`, this is a no-op.
```k
  syntax KItem ::= "#PC" "[" Instruction "]"

  rule <instrs> #PC[ I ] => .K ...</instrs>
       <pc> PC => PC +Word pcIncrAmount(I) </pc>

  syntax Word ::= pcIncrAmount(Instruction) [function, total]
  rule pcIncrAmount(_)                => W(4) [owise]
```

R-Type Instructions

```k
  rule <instrs> AND RD , RN , RM => .K ...</instrs>
       <regs> REGS => writeReg(REGS, RD, readReg(REGS, RN) &Word readReg(REGS, RM)) </regs>
 
  rule <instrs> ADD RD , RN , RM => .K ...</instrs>
       <regs> REGS => writeReg(REGS, RD, readReg(REGS, RN) +Word readReg(REGS, RM)) </regs>
 
  rule <instrs> SDIV RD , RN , RM => .K ...</instrs>
       <regs> REGS => writeReg(REGS, RD, readReg(REGS, RN) /sWord readReg(REGS, RM)) </regs>

  rule <instrs> UDIV RD , RN , RM => .K ...</instrs>
       <regs> REGS => writeReg(REGS, RD, readReg(REGS, RN) /uWord readReg(REGS, RM)) </regs>
```

I-Type Instructions


```k
  rule <instrs> ADDI RD , RN , # IMM => .K ...</instrs>
       <regs> REGS => writeReg(REGS, RD, readReg(REGS, RN) +Word chop(IMM)) </regs>
```

D-Type Instructions

rule <instrs> LW RD , OFFSET ( RS1 ) => .K ...</instrs>
       <regs> REGS => writeReg(REGS, RD, signExtend(loadBytes(MEM, readReg(REGS, RS1) +Word chop(OFFSET), 4), 32)) </regs>
       <mem> MEM </mem>

```k
endmodule
```
