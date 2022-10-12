import opcode, uuid, dis
import typing, types

EXTENDED_ARG = opcode.opmap["EXTENDED_ARG"]

# All jumps
relative_jumps = dis.hasjrel
absolute_jumps = dis.hasjabs


class Instruction:
    def __init__(self, opcode, arg, uid=None, jump_target=None):
        self.opcode = opcode
        self.arg = arg
        self.jump_target = jump_target
        if uid is None:
            self.uid = uuid.uuid4()
        else:
            self.uid = uid

    def __repr__(self):
        return f"<Instruction opcode={opcode.opname[self.opcode]}, arg={self.arg}, uid={self.uid}, jump_target={self.jump_target}>"


def calculate_extended_args(arg):
    extended_args = []
    new_arg = arg
    if arg > 255:
        extended_arg = arg >> 8
        while True:
            if extended_arg > 255:
                extended_arg -= 255
                extended_args.append(255)
            else:
                extended_args.append(extended_arg)
                break

        new_arg = arg % 256
    return extended_args, new_arg


class Code:
    def __init__(self, code):
        self.uid = uuid.uuid4()
        for attr in dir(code):
            if attr.startswith("co_"):
                setattr(self, attr, getattr(code, attr))

    def resolve_jumps(self) -> typing.List[Instruction]:
        new_insts = []
        for inst in self.co_code:
            if inst.opcode in relative_jumps or inst.opcode in absolute_jumps:
                target = [e for e in self.co_code if e.uid == inst.jump_target]

                # assert len(target) != 0, "Invalid target " + str(inst.jump_target)

                if len(target) == 0:
                    inst.arg = inst.jump_target
                else:
                    target = target[0]

                    if inst.opcode in relative_jumps:
                        inst.arg = (self.co_code.index(target) * 2) - (len(new_insts) * 2)
                    else:
                        inst.arg = self.co_code.index(target) * 2

            new_insts.append(inst)

        return new_insts

    def code2bytes(self) -> bytes:
        if isinstance(self.co_code, list):
            self.co_code = self.resolve_jumps()
            new = bytearray()

            for inst in self.co_code:
                extended_args, new_arg = calculate_extended_args(inst.arg)

                for extended_arg in extended_args:
                    print("used")
                    new.append(EXTENDED_ARG)
                    new.append(extended_arg)

                new.append(inst.opcode)
                new.append(new_arg)

            return bytes(new)

    def to_native(self, code_objects=None) -> types.CodeType:
        def empty():
            pass

        self.co_code = self.code2bytes()
        new_consts = []
        for const in self.co_consts:
            if isinstance(const, Code):
                code_objects = self.code_objects if getattr(self, "code_objects", None) else code_objects
                code = [e for e in code_objects if str(const.uid) == str(e.uid)]
                const = code[0].to_native()

            new_consts.append(const)

        self.co_consts = tuple(new_consts)

        return empty.__code__.replace(**{key: value for key, value in vars(self).items() if key.startswith("co_")})

    def __repr__(self):
        return f"<Code object {self.co_name} at {hex(id(self))}"


def bytes2insts(co_code: bytes) -> typing.List[Instruction]:
    instructions = []
    i = 0
    while i < len(co_code):
        op = co_code[i]
        arg = co_code[i + 1]
        if op != EXTENDED_ARG:
            instructions.append(Instruction(op, arg))
        else:
            real_arg = bytearray()
            while op == EXTENDED_ARG:
                real_arg.insert(0, arg)

                i += 2
                op = co_code[i]
                arg = co_code[i + 1]

            real_arg.append(arg)
            instructions.append(Instruction(op, int.from_bytes(real_arg, 'big')))

        i += 2

    return instructions


def set_jump_targets(co_code: typing.List[Instruction]) -> typing.List[Instruction]:
    new_insts = []
    for i, inst in enumerate(co_code):
        if inst.opcode in relative_jumps:
            try:
                jump_target = co_code[i + (inst.arg // 2)].uid
            except IndexError:
                jump_target = inst.arg

            inst = Instruction(inst.opcode, inst.arg, inst.uid, jump_target)
        elif inst.opcode in absolute_jumps:
            try:
                jump_target = co_code[inst.arg // 2].uid
            except IndexError:
                jump_target = inst.arg

            inst = Instruction(inst.opcode, inst.arg, inst.uid, jump_target)

        new_insts.append(inst)

    return new_insts


def code2custom(code: types.CodeType, make_list=True) -> Code:
    tree = {}
    code = Code(code)
    code.co_code = bytes2insts(code.co_code)
    code.co_code = set_jump_targets(code.co_code)
    code_objects = []

    new_consts = []
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            const, const_code_objects, const_tree = code2custom(const, make_list=False)
            code_objects.extend(const_code_objects)
            tree[const] = const_tree
            code_objects.append(const)

        new_consts.append(const)

    code.co_consts = new_consts

    if make_list:
        code.code_objects = code_objects
        code.tree = tree
        return code

    return code, code_objects, tree if tree else None
