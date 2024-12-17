# Instruction Syntax
In this file, we define the basic syntax for disassembled instructions.

We closely mirror the ASM syntax as output by the LEGv8 GNU Toolchain's `objdump`. In particular,
- I-Type and S-Type instructions with 12-bit signed immediates (e.g., `addi` but not `slli`) take an immediate argument in the range `[-2048, 2047]`.
- Shift instructions take a shift amount argument in the range `[0, XLEN - 1]`.
- U-Type instruction take an immediate argument in the range `[0x0, 0xfffff]`, i.e., not representing the zeroed-out 12 least-significant bits.
- B-Type instructions take an immediate argument as an even integer in the range `[-4096, 4094]`, i.e., explicitly representing the zeroed-out least-significant bit.
- J-Type instructions take an immediate argument as an even integer in the range `[-1048576, 1048574]`, i.e., explicitly representing the zeroed-out least-significant bit.

A register `xi` is simply represented by the `Int` value `i`.
```k
module LEGV8-INSTRUCTIONS
  imports INT

  syntax Register ::= Int

  syntax Instruction ::=
      RegRegRegInstr
    | RegRegImmInstr
    | RegRegImmBracketInstr
    | InvalidInstr

  syntax RegRegRegInstr ::= RegRegRegInstrName Register "," Register "," Register [symbol(RegRegRegInstr)]
  syntax RegRegRegInstrName ::=
      "AND"   [symbol(AND)]
    | "ADD"   [symbol(ADD)]
    | "SDIV"  [symbol(SDIV)]
    | "UDIV"  [symbol(UDIV)]    
    | "MUL"   [symbol(MUL)] 
    | "ORR"   [symbol(ORR)] 
    | "ADDS"  [symbol(ADDS)]  
    | "EOR"   [symbol(EOR)] 
    | "SUB"   [symbol(SUB)] 
    | "LSR"   [symbol(LSR)] 
    | "LSL"   [symbol(LSL)] 
  
  syntax RegRegImmInstr ::= RegRegImmInstrName Register "," Register "," "#" Int [symbol(RegRegImmInstr)]
  syntax RegRegImmInstrName ::=
      "ADDI"   [symbol(ADDI)]

  syntax RegRegImmBracketInstr ::= RegRegImmBracketInstrName Register "," "[" Register ","  "#" Int "]" [symbol(RegRegImmBracketInstr)]
  syntax RegRegImmBracketInstrName ::=
      "LDUR"   [symbol(LDUR)]

  syntax InvalidInstr ::= "INVALID_INSTR" [symbol(INVALID_INSTR)]
endmodule
```
