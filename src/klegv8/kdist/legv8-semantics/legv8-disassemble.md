# Disassembler
In this file, we implement the instruction disassembler, converting raw instruction bits to the syntax defined in [legv8-intructions.md](./legv8-instructions.md).
```k
requires "legv8-instructions.md"
requires "word.md"

module LEGV8-DISASSEMBLE
  imports LEGV8-INSTRUCTIONS
  imports INT
  imports STRING
  imports WORD
```
The input is given as an `Int` with the instruction stored in the 32 least-significant bits.
```k
  syntax Instruction ::= disassemble(Int) [symbol(disassemble), function, total, memo]
  rule disassemble(I:Int) => disassemble(decode(I))
```
Disassembly is then done in two phases:
- Separate out the component fields of the instruction based on its format (R, I, D, B, CB or IW), returning an `InstructionFormat` value.
- Inspect the fields of the resulting `InstructionFormat` to produce the disassembled instruction.

The various `InstructionFormat`s are defined below.
```k
  syntax InstructionFormat ::=
      RType(opcode: RTypeOpCode, Rm: Register, shamt: Int, Rn: Register, Rd: Register)
    | IType(opcode: ITypeOpCode, ALUImm: Int, Rn: Register, Rd: Register)
    | DType(opcode: DTypeOpCode, DTAddr: Int, op: Int, Rn: Register, Rt: Register)
    | UnrecognizedInstructionFormat(Int)
```
We determine the correct format by decoding the op code from the 7 least-signficant bits,
```k
  syntax OpCode ::=
      RTypeOpCode
    | ITypeOpCode
    | DTypeOpCode
    | UnrecognizedOpCode

  syntax RTypeOpCode ::=
      "AND"
    | "ADD"
    | "DIV"
    | "MUL"
    | "ORR"
    | "ADDS"
    | "EOR"
    | "SUB"
    | "LSR"
    | "LSL"

  syntax ITypeOpCode ::= 
      "ADDI"
    | "ANDI"

  syntax DTypeOpCode ::=
      "LDUR"
  
  syntax UnrecognizedOpCode ::=
      "UNRECOGNIZED"

  syntax OpCode ::= decodeOpCode(Int) [function, total]
  rule decodeOpCode(I:Int ) => AND requires  ((I >>Int 21) &Int 2047) ==Int 1104
  rule decodeOpCode(I:Int ) => ADD requires  ((I >>Int 21) &Int 2047) ==Int 1112
  rule decodeOpCode(I:Int ) => DIV requires ((I >>Int 21) &Int 2047) ==Int 1238
  rule decodeOpCode(I:Int ) => ADDI requires ((I >>Int 22) &Int 1023) ==Int 580
  rule decodeOpCode(I:Int ) => LDUR requires ((I >>Int 21) &Int 2047) ==Int 1986
  // rule decodeOpCode(I:Int ) => UDIV requires (I &Int 2047) ==Int 1238
  // rule decodeOpCode(I:Int ) => MUL requires (I &Int 2047) ==Int 1240
  // rule decodeOpCode(I:Int ) => ORR requires (I &Int 2047) ==Int 1360
  // rule decodeOpCode(I:Int ) => ADDS requires (I &Int 2047) ==Int 1368
  // rule decodeOpCode(I:Int ) => EOR requires (I &Int 2047) ==Int 1616
  // rule decodeOpCode(I:Int ) => SUB requires (I &Int 2047) ==Int 1624
  // rule decodeOpCode(I:Int ) => LSR requires (I &Int 2047) ==Int 1690
  // rule decodeOpCode(I:Int ) => LSL requires (I &Int 2047) ==Int 1691
  rule decodeOpCode(_  ) => UNRECOGNIZED [owise]
```
matching on the type of the resulting opcode,
```k
  syntax InstructionFormat ::= decode(Int) [function, total]
  rule decode(I) => decodeWithOp(decodeOpCode(I), I)
```
then finally bit-fiddling to mask out the appropriate bits for each field.
```k
  syntax InstructionFormat ::= decodeWithOp(OpCode, Int) [function]

  rule decodeWithOp(OPCODE:RTypeOpCode, I) =>
    RType(OPCODE, (I >>Int 16) &Int 31, (I >>Int 10) &Int 63, (I >>Int 5) &Int 31, I &Int 31)
  rule decodeWithOp(OPCODE:ITypeOpCode, I) =>
    IType(OPCODE, (I >>Int 10) &Int 4095, (I >>Int 5) &Int 31, I &Int 31)
  rule decodeWithOp(OPCODE:DTypeOpCode, I) =>
    DType(OPCODE, (I >>Int 12) &Int 511, (I >>Int 10) &Int 3, (I >>Int 5) &Int 31, I &Int 31)
  rule decodeWithOp(_:UnrecognizedOpCode, I) =>
    UnrecognizedInstructionFormat(I)
```
Finally, we can disassemble the instruction by inspecting the fields for each format. Note that, where appropriate, we infinitely sign extend immediates to represent them as K `Int`s.
```k
  syntax Instruction ::= disassemble(InstructionFormat) [function, total]

  rule disassemble(RType(AND, RM, 0, RN, RD)) => AND  RD , RN , RM
  rule disassemble(RType(ADD, RM, 0, RN, RD)) => ADD  RD , RN , RM
  rule disassemble(RType(DIV, RM, 2, RN, RD)) => SDIV  RD , RN , RM
  rule disassemble(RType(DIV, RM, 3, RN, RD)) => UDIV  RD , RN , RM
  rule disassemble(RType(MUL, RM, 31, RN, RD)) => MUL  RD , RN , RM
  rule disassemble(RType(ORR, RM, 0, RN, RD)) => ORR  RD , RN , RM
  rule disassemble(RType(ADDS, RM, 0, RN, RD)) => ADDS  RD , RN , RM
  rule disassemble(RType(EOR, RM, 0, RN, RD)) => EOR  RD , RN , RM
  rule disassemble(RType(SUB, RM, 0, RN, RD)) => SUB  RD , RN , RM
  rule disassemble(RType(LSR, RM, 0, RN, RD)) => LSR  RD , RN , RM
  rule disassemble(RType(LSL, RM, 0, RN, RD)) => LSL  RD , RN , RM

  rule disassemble(IType(ADDI, IMM, RN, RD)) => ADDI  RD , RN , # infSignExtend(IMM, 12)

  rule disassemble(DType(LDUR, IMM, 0, RT, RN)) => LDUR  RT , [RN, # infSignExtend(IMM, 12)]  

  rule disassemble(_:InstructionFormat) => INVALID_INSTR [owise]
endmodule
```
