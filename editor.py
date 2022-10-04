import opcode, uuid, dis

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


class Code:
    def __init__(self, code):
        for attr in dir(code):
            if attr.startswith("co_"):
                setattr(self, attr, getattr(code, attr))

    def resolve_jumps(self):
        new_insts = []
        for inst in self.co_code:
            if inst.opcode in relative_jumps or inst.opcode in absolute_jumps:
                target = [e for e in self.co_code if e.uid == inst.jump_target]

                assert len(target) != 0, "Invalid target " + str(inst.jump_target)

                target = target[0]
                if inst.opcode in relative_jumps:
                    inst.arg = (self.co_code.index(target) * 2) - (len(new_insts) * 2)
                else:
                    inst.arg = self.co_code.index(target) * 2

            new_insts.append(inst)

        return new_insts

    def calculate_extended_args(self, arg):
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

    def code2bytes(self):
        if isinstance(self.co_code, list):
            self.co_code = self.resolve_jumps()
            new = bytearray()

            for inst in self.co_code:
                extended_args, new_arg = self.calculate_extended_args(inst.arg)

                for extended_arg in extended_args:
                    print("used")
                    new.append(EXTENDED_ARG)
                    new.append(extended_arg)

                new.append(inst.opcode)
                new.append(new_arg)

            return bytes(new)

    def to_native(self):
        def empty():
            pass

        self.co_code = self.code2bytes()

        return empty.__code__.replace(**{key: value for key, value in vars(self).items() if key.startswith("co_")})


def bytes2insts(co_code):
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


def set_jump_targets(co_code):
    new_insts = []
    for i, inst in enumerate(co_code):
        if inst.opcode in relative_jumps:
            inst = Instruction(inst.opcode, inst.arg, inst.uid, co_code[i + (inst.arg // 2)].uid)
        elif inst.opcode in absolute_jumps:
            inst = Instruction(inst.opcode, inst.arg, inst.uid, co_code[inst.arg // 2].uid)

        new_insts.append(inst)

    return new_insts


def code2custom(code):
    obj = Code(code)
    obj.co_code = bytes2insts(obj.co_code)
    obj.co_code = set_jump_targets(obj.co_code)

    return obj
