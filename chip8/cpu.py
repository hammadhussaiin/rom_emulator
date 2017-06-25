import pygame
from exception import UnknownOpCodeException
from pygame import key
from random import randint
from addresses import *

# The total amount of memory to allocate for the emulator
MAX_MEMORY = 4096

# Where the stack pointer should originally point
STACK_POINTER_START = 0x52

# Where the program counter should originally point
PROGRAM_COUNTER_START = 0x200

# Sets which keys on the keyboard map to the Chip 8 keys
KEY_MAPPINGS = {
    0x0: pygame.K_KP0,
    0x1: pygame.K_KP1,
    0x2: pygame.K_KP2,
    0x3: pygame.K_KP3,
    0x4: pygame.K_KP4,
    0x5: pygame.K_KP5,
    0x6: pygame.K_KP6,
    0x7: pygame.K_KP7,
    0x8: pygame.K_KP8,
    0x9: pygame.K_KP9,
    0xA: pygame.K_a,
    0xB: pygame.K_b,
    0xC: pygame.K_c,
    0xD: pygame.K_d,
    0xE: pygame.K_e,
    0xF: pygame.K_f,
}

# The total number of registers in the Chip 8 CPU
NUM_REGISTERS = 0x10

# The various modes of operation
MODE_NORMAL = 'normal'
MODE_EXTENDED = 'extended'

# C L A S S E S ###############################################################


class CPU(object):
    """
    A class to emulate a Chip 8 CPU. There are several good resources out on
    the web that describe the internals of the Chip 8 CPU. For example:

        http://devernay.free.fr/hacks/chip8/C8TECH10.HTM
        http://michael.toren.net/mirrors/chip8/chip8def.htm

    As usual, a simple Google search will find you other excellent examples.
    To summarize these sources, the Chip 8 has:

        * 16 x 8-bit general purpose registers (V0 - VF**)
        * 1 x 16-bit index register (I)
        * 1 x 16-bit stack pointer (SP)
        * 1 x 16-bit program counter (PC)
        * 1 x 8-bit delay timer (DT)
        * 1 x 8-bit sound timer (ST)

    ** VF is a special register - it is used to store the overflow bit
    """
    def __init__(self, screen):
        """
        Initialize the Chip8 CPU. The only required parameter is a screen
        object that supports the draw_pixel function. For testing purposes,
        this can be set to None.

        :param screen: the screen object to draw pixels on
        """
        # There are two timer registers, one for sound and one that is general
        # purpose known as the delay timer. The timers are loaded with a value
        # and then decremented 60 times per second.
        self.cpu_timers = {
            'delay': 0,
            'sound': 0,
        }

        # Defines the general purpose, index, stack pointer and program
        # counter registers.
        self.cpu_registers = {
            'v': [],
            'index': 0,
            'sp': 0,
            'pc': 0,
            'rpl': []
        }

        # The operation_lookup table is executed according to the most
        # significant byte of the operand (e.g. operand 8nnn would call
        # self.execute_logical_instruction)
        self.cpu_operation_lookup = {
            0x0: self.cpu_clear_return,                  # 0nnn - SYS  nnn
            0x1: self.cpu_jump_to_address,               # 1nnn - JUMP nnn
            0x2: self.cpu_jump_to_subroutine,            # 2nnn - CALL nnn
            0x3: self.cpu_skip_if_reg_equal_val,         # 3snn - SKE  Vs, nn
            0x4: self.cpu_skip_if_reg_not_equal_val,     # 4snn - SKNE Vs, nn
            0x5: self.cpu_skip_if_reg_equal_reg,         # 5st0 - SKE  Vs, Vt
            0x6: self.cpu_move_value_to_reg,             # 6snn - LOAD Vs, nn
            0x7: self.cpu_add_value_to_reg,              # 7snn - ADD  Vs, nn
            0x8: self.cpu_execute_logical_instruction,   # see subfunctions below
            0x9: self.cpu_skip_if_reg_not_equal_reg,     # 9st0 - SKNE Vs, Vt
            0xA: self.cpu_load_index_reg_with_value,     # Annn - LOAD I, nnn
            0xB: self.cpu_jump_to_index_plus_value,      # Bnnn - JUMP [I] + nnn
            0xC: self.cpu_generate_random_number,        # Ctnn - RAND Vt, nn
            0xD: self.cpu_draw_sprite,                   # Dstn - DRAW Vs, Vy, n
            0xE: self.cpu_keyboard_routines,             # see subfunctions below
            0xF: self.cpu_misc_routines,                 # see subfunctions below
        }

        # This set of operations is invoked when the operand loaded into the
        # CPU starts with 8 (e.g. operand 8nn0 would call
        # self.move_reg_into_reg)
        self.cpu_logical_operation_lookup = {
            0x0: self.cpu_move_reg_into_reg,             # 8st0 - LOAD Vs, Vt
            0x1: self.cpu_logical_or,                    # 8st1 - OR   Vs, Vt
            0x2: self.cpu_logical_and,                   # 8st2 - AND  Vs, Vt
            0x3: self.cpu_exclusive_or,                  # 8st3 - XOR  Vs, Vt
            0x4: self.cpu_add_reg_to_reg,                # 8st4 - ADD  Vs, Vt
            0x5: self.cpu_subtract_reg_from_reg,         # 8st5 - SUB  Vs, Vt
            0x6: self.cpu_right_shift_reg,               # 8st6 - SHR  Vs
            0x7: self.cpu_subtract_reg_from_reg1,        # 8st7 - SUBN Vs, Vt
            0xE: self.cpu_left_shift_reg,                # 8stE - SHL  Vs
        }

        # This set of operations is invoked when the operand loaded into the
        # CPU starts with F (e.g. operand Fn07 would call
        # self.move_delay_timer_into_reg)
        self.cpu_misc_routine_lookup = {
            0x07: self.cpu_move_delay_timer_into_reg,            # Ft07 - LOAD Vt, DELAY
            0x0A: self.cpu_wait_for_keypress,                    # Ft0A - KEYD Vt
            0x15: self.cpu_move_reg_into_delay_timer,            # Fs15 - LOAD DELAY, Vs
            0x18: self.cpu_move_reg_into_sound_timer,            # Fs18 - LOAD SOUND, Vs
            0x1E: self.cpu_add_reg_into_index,                   # Fs1E - ADD  I, Vs
            0x29: self.cpu_load_index_with_reg_sprite,           # Fs29 - LOAD I, Vs
            0x30: self.cpu_load_index_with_extended_reg_sprite,  # Fs30 - LOAD I, Vs
            0x33: self.cpu_store_bcd_in_memory,                  # Fs33 - BCD
            0x55: self.cpu_store_regs_in_memory,                 # Fs55 - STOR [I], Vs
            0x65: self.cpu_read_regs_from_memory,                # Fs65 - LOAD Vs, [I]
            0x75: self.cpu_store_regs_in_rpl,                    # Fs75 - SRPL Vs
            0x85: self.cpu_read_regs_from_rpl,                   # Fs85 - LRPL Vs
        }
        self.cpu_operand = 0
        self.cpu_mode = MODE_NORMAL
        self.cpu_screen = screen
        self.cpu_memory = bytearray(MAX_MEMORY)
        self.cpu_reset()

    def __str__(self):
        val = 'PC: {:4X}  OP: {:4X}\n'.format(
            self.cpu_registers['pc'] - 2, self.operand)
        for index in range(0x10):
            val += 'V{:X}: {:2X}\n'.format(index, self.cpu_registers['v'][index])
        val += 'I: {:4X}\n'.format(self.cpu_registers['index'])
        return val

    def cpu_execute_instruction(self, cpu_operator_param=None):
        """
        Execute the next instruction pointed to by the program counter.
        For testing purposes, pass the operand directly to the
        function. When the operand is not passed directly to the
        function, the program counter is increased by 2.

        :param operand: the operand to execute
        :return: returns the operand executed
        """
        if cpu_operator_param:
            self.cpu_operand = cpu_operator_param
        else:
            self.cpu_operand = int(self.cpu_memory[self.cpu_registers['pc']])
            self.cpu_operand <<= 8
            self.cpu_operand += int(self.cpu_memory[self.cpu_registers['pc'] + 1])
            self.cpu_registers['pc'] += 2
        cpu_operation = (self.cpu_operand & ADDRESS_1) >> 12
        self.cpu_operation_lookup[cpu_operation]()
        return self.cpu_operand

    def cpu_execute_logical_instruction(self):
        """
        Execute the logical instruction based upon the current operand.
        For testing purposes, pass the operand directly to the function.
        """
        cpu_operation = self.cpu_operand & ADDRESS_6
        try:
            self.cpu_logical_operation_lookup[cpu_operation]()
        except KeyError:
            raise UnknownOpCodeException(self.cpu_operand)

    def cpu_keyboard_routines(self):
        """
        Run the specified keyboard routine based upon the operand. These
        operations are:

            Es9E - SKPR Vs
            EsA1 - SKUP Vs

        0x9E will check to see if the key specified in the source register is
        pressed, and if it is, skips the next instruction. Operation 0xA1 will
        again check for the specified keypress in the source register, and
        if it is NOT pressed, will skip the next instruction. The register
        calculations are as follows:

           Bits:  15-12    11-8      7-4      3-0
                  unused   source  9 or A    E or 1
        """
        cpu_operation = self.cpu_operand & ADDRESS_2
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8

        cpu_key_to_check = self.cpu_registers['v'][cpu_source]
        cpu_keys_pressed = key.get_pressed()

        # Skip if the key specified in the source register is pressed
        if cpu_operation == 0x9E:
            if cpu_keys_pressed[KEY_MAPPINGS[cpu_key_to_check]]:
                self.cpu_registers['pc'] += 2

        # Skip if the key specified in the source register is not pressed
        if cpu_operation == 0xA1:
            if not cpu_keys_pressed[KEY_MAPPINGS[cpu_key_to_check]]:
                self.cpu_registers['pc'] += 2

    def cpu_misc_routines(self):
        """
        Will execute one of the routines specified in misc_routines.
        """
        cpu_operation = self.cpu_operand & ADDRESS_2
        try:
            self.cpu_misc_routine_lookup[cpu_operation]()
        except KeyError:
            raise UnknownOpCodeException(self.cpu_operand)

    def cpu_clear_return(self):
        """
        Opcodes starting with a 0 are one of the following instructions:

            0nnn - Jump to machine code function (ignored)
            00Cn - Scroll n pixels down
            00E0 - Clear the display
            00EE - Return from subroutine
            00FB - Scroll 4 pixels right
            00FC - Scroll 4 pixels left
            00FD - Exit
            00FE - Disable extended mode
            00FF - Enable extended mode
        """
        cpu_operation = self.cpu_operand & ADDRESS_2
        cpu_sub_operation = cpu_operation & ADDRESS_4
        if cpu_sub_operation == ADDRESS_5:
            num_lines = self.cpu_operand & ADDRESS_6
            self.cpu_screen.scroll_screen_down(num_lines)

        if cpu_operation == ADDRESS_7:
            self.cpu_screen.clear_screen()

        if cpu_operation == ADDRESS_8:
            self.cpu_registers['sp'] -= 1
            self.cpu_registers['pc'] = self.cpu_memory[self.cpu_registers['sp']] << 8
            self.cpu_registers['sp'] -= 1
            self.cpu_registers['pc'] += self.cpu_memory[self.cpu_registers['sp']]

        if cpu_operation == ADDRESS_9:
            self.cpu_screen.scroll_screen_right()

        if cpu_operation == ADDRESS_10:
            self.cpu_screen.scroll_screen_left()

        if cpu_operation == ADDRESS_11:
            pass

        if cpu_operation == ADDRESS_12:
            self.cpu_screen.set_screen_normal()
            self.cpu_mode = MODE_NORMAL

        if cpu_operation == ADDRESS_2:
            self.cpu_screen.set_screen_extended()
            self.cpu_mode = MODE_EXTENDED

    def cpu_jump_to_address(self):
        """
        1nnn - JUMP nnn

        Jump to address. The address to jump to is calculated using the bits
        taken from the operand as follows:

           Bits:  15-12    11-8      7-4      3-0
                  unused  address  address  address
        """
        self.cpu_registers['pc'] = self.cpu_operand & ADDRESS_13

    def cpu_jump_to_subroutine(self):
        """
        2nnn - CALL nnn

        Jump to subroutine. Save the current program counter on the stack. The
        subroutine to jump to is taken from the operand as follows:

           Bits:  15-12    11-8      7-4      3-0
                  unused  address  address  address
        """
        self.cpu_memory[self.cpu_registers['sp']] = self.cpu_registers['pc'] & ADDRESS_2
        self.cpu_registers['sp'] += 1
        self.cpu_memory[self.cpu_registers['sp']] = (self.cpu_registers['pc'] & ADDRESS_14) >> 8
        self.cpu_registers['sp'] += 1
        self.cpu_registers['pc'] = self.cpu_operand & ADDRESS_13

    def cpu_skip_if_reg_equal_val(self):
        """
        3snn - SKE Vs, nn

        Skip if register contents equal to constant value. The calculation for
        the register and constant is performed on the operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   source  constant  constant

        The program counter is updated to skip the next instruction by
        advancing it by 2 bytes.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        if self.cpu_registers['v'][cpu_source] == (self.cpu_operand & ADDRESS_2):
            self.cpu_registers['pc'] += 2

    def cpu_skip_if_reg_not_equal_val(self):
        """
        4snn - SKNE Vs, nn

        Skip if register contents not equal to constant value. The calculation
        for the register and constant is performed on the operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   source  constant  constant

        The program counter is updated to skip the next instruction by
        advancing it by 2 bytes.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        if self.cpu_registers['v'][cpu_source] != (self.cpu_operand & ADDRESS_2):
            self.cpu_registers['pc'] += 2

    def cpu_skip_if_reg_equal_reg(self):
        """
        5st0 - SKE Vs, Vt

        Skip if source register is equal to target register. The calculation
        for the registers to use is performed on the operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   source    target      0

        The program counter is updated to skip the next instruction by
        advancing it by 2 bytes.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_target = (self.cpu_operand & ADDRESS_4) >> 4
        if self.cpu_registers['v'][cpu_source] == self.cpu_registers['v'][cpu_target]:
            self.cpu_registers['pc'] += 2

    def cpu_move_value_to_reg(self):
        """
        6snn - LOAD Vs, nn

        Move the constant value into the specified register. The calculation
        for the registers is performed on the operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    value     value
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_registers['v'][cpu_target] = self.cpu_operand & ADDRESS_2

    def cpu_add_value_to_reg(self):
        """
        7snn - ADD Vs, nn

        Add the constant value to the specified register. The calculation
        for the registers is performed on the operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    value     value
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        temp = self.cpu_registers['v'][cpu_target] + (self.cpu_operand & ADDRESS_2)
        self.cpu_registers['v'][cpu_target] = temp if temp < 256 else temp - 256

    def cpu_move_reg_into_reg(self):
        """
        8st0 - LOAD Vs, Vt

        Move the value of the source register into the value of the target
        register. The calculation for the registers is performed on the
        operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    source      0
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_source = (self.cpu_operand & ADDRESS_4) >> 4
        self.cpu_registers['v'][cpu_target] = self.cpu_registers['v'][cpu_source]

    def cpu_logical_or(self):
        """
        8ts1 - OR   Vs, Vt

        Perform a logical OR operation between the source and the target
        register, and store the result in the target register. The register
        calculations are as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    source      1
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_source = (self.cpu_operand & ADDRESS_4) >> 4
        self.cpu_registers['v'][cpu_target] |= self.cpu_registers['v'][cpu_source]

    def cpu_logical_and(self):
        """
        8ts2 - AND  Vs, Vt

        Perform a logical AND operation between the source and the target
        register, and store the result in the target register. The register
        calculations are as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    source      2
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_source = (self.cpu_operand & ADDRESS_4) >> 4
        self.cpu_registers['v'][cpu_target] &= self.cpu_registers['v'][cpu_source]

    def cpu_exclusive_or(self):
        """
        8ts3 - XOR  Vs, Vt

        Perform a logical XOR operation between the source and the target
        register, and store the result in the target register. The register
        calculations are as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    source      3
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_source = (self.cpu_operand & ADDRESS_4) >> 4
        self.cpu_registers['v'][cpu_target] ^= self.cpu_registers['v'][cpu_source]

    def cpu_add_reg_to_reg(self):
        """
        8ts4 - ADD  Vt, Vs

        Add the value in the source register to the value in the target
        register, and store the result in the target register. The register
        calculations are as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    source      4

        If a carry is generated, set a carry flag in register VF.
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_source = (self.cpu_operand & ADDRESS_4) >> 4
        temp = self.cpu_registers['v'][cpu_target] + self.cpu_registers['v'][cpu_source]
        if temp > 255:
            self.cpu_registers['v'][cpu_target] = temp - 256
            self.cpu_registers['v'][0xF] = 1
        else:
            self.cpu_registers['v'][cpu_target] = temp
            self.cpu_registers['v'][0xF] = 0

    def cpu_subtract_reg_from_reg(self):
        """
        8ts5 - SUB  Vt, Vs

        Subtract the value in the target register from the value in the source
        register, and store the result in the target register. The register
        calculations are as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    source      5

        If a borrow is NOT generated, set a carry flag in register VF.
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_source = (self.cpu_operand & ADDRESS_4) >> 4
        cpu_source_reg = self.cpu_registers['v'][cpu_source]
        cpu_target_reg = self.cpu_registers['v'][cpu_target]
        if cpu_target_reg > cpu_source_reg:
            cpu_target_reg -= cpu_source_reg
            self.cpu_registers['v'][0xF] = 1
        else:
            cpu_target_reg = 256 + cpu_target_reg - cpu_source_reg
            self.cpu_registers['v'][0xF] = 0
        self.cpu_registers['v'][cpu_target] = cpu_target_reg

    def cpu_right_shift_reg(self):
        """
        8s06 - SHR  Vs

        Shift the bits in the specified register 1 bit to the right. Bit
        0 will be shifted into register vf. The register calculation is
        as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   source      0         6
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_bit_zero = self.cpu_registers['v'][cpu_source] & 0x1
        self.cpu_registers['v'][cpu_source] = self.cpu_registers['v'][cpu_source] >> 1
        self.cpu_registers['v'][0xF] = cpu_bit_zero

    def cpu_subtract_reg_from_reg1(self):
        """
        8ts7 - SUBN Vt, Vs

        Subtract the value in the source register from the value in the target
        register, and store the result in the target register. The register
        calculations are as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   target    source      7

        If a borrow is NOT generated, set a carry flag in register VF.
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_source = (self.cpu_operand & ADDRESS_4) >> 4
        cpu_source_reg = self.cpu_registers['v'][cpu_source]
        cpu_target_reg = self.cpu_registers['v'][cpu_target]
        if cpu_source_reg > cpu_target_reg:
            cpu_target_reg = cpu_source_reg - cpu_target_reg
            self.cpu_registers['v'][0xF] = 1
        else:
            cpu_target_reg = 256 + cpu_source_reg - cpu_target_reg
            self.cpu_registers['v'][0xF] = 0
        self.cpu_registers['v'][cpu_target] = cpu_target_reg

    def cpu_left_shift_reg(self):
        """
        8s0E - SHL  Vs

        Shift the bits in the specified register 1 bit to the left. Bit
        7 will be shifted into register vf. The register calculation is
        as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   source      0         E
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_bit_seven = (self.cpu_registers['v'][cpu_source] & 0x80) >> 8
        self.cpu_registers['v'][cpu_source] = self.cpu_registers['v'][cpu_source] << 1
        self.cpu_registers['v'][0xF] = cpu_bit_seven

    def cpu_skip_if_reg_not_equal_reg(self):
        """
        9st0 - SKNE Vs, Vt

        Skip if source register is equal to target register. The calculation
        for the registers to use is performed on the operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   source    target    unused

        The program counter is updated to skip the next instruction by
        advancing it by 2 bytes.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_target = (self.cpu_operand & ADDRESS_4) >> 4
        if self.cpu_registers['v'][cpu_source] != self.cpu_registers['v'][cpu_target]:
            self.cpu_registers['pc'] += 2

    def cpu_load_index_reg_with_value(self):
        """
        Annn - LOAD I, nnn

        Load index register with constant value. The calculation for the
        constant value is performed on the operand:

           Bits:  15-12     11-8      7-4       3-0
                  unused   constant  constant  constant
        """
        self.cpu_registers['index'] = self.cpu_operand & ADDRESS_13

    def cpu_jump_to_index_plus_value(self):
        """
        Bnnn - JUMP [I] + nnn

        Load the program counter with the memory value located at the specified
        operand plus the value of the index register. The address calculation
        is based on the operand, masked as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused   address  address  address
        """
        self.cpu_registers['pc'] = self.cpu_registers['index'] + (self.cpu_operand & ADDRESS_13)

    def cpu_generate_random_number(self):
        """
        Ctnn - RAND Vt, nn

        A random number between 0 and 255 is generated. The contents of it are
        then ANDed with the constant value passed in the operand. The result is
        stored in the target register. The register and constant values are
        calculated as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused    target    value    value
        """
        cpu_value = self.cpu_operand & ADDRESS_2
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_registers['v'][cpu_target] = cpu_value & randint(0, 255)

    def cpu_draw_sprite(self):
        """
        Dxyn - DRAW x, y, num_bytes

        Draws the sprite pointed to in the index register at the specified
        x and y coordinates. Drawing is done via an XOR routine, meaning that
        if the target pixel is already turned on, and a pixel is set to be
        turned on at that same location via the draw, then the pixel is turned
        off. The routine will wrap the pixels if they are drawn off the edge
        of the screen. Each sprite is 8 bits (1 byte) wide. The num_bytes
        parameter sets how tall the sprite is. Consecutive bytes in the memory
        pointed to by the index register make up the bytes of the sprite. Each
        bit in the sprite byte determines whether a pixel is turned on (1) or
        turned off (0). For example, assume that the index register pointed
        to the following 7 bytes:

                       bit 0 1 2 3 4 5 6 7

           byte 0          0 1 1 1 1 1 0 0
           byte 1          0 1 0 0 0 0 0 0
           byte 2          0 1 0 0 0 0 0 0
           byte 3          0 1 1 1 1 1 0 0
           byte 4          0 1 0 0 0 0 0 0
           byte 5          0 1 0 0 0 0 0 0
           byte 6          0 1 1 1 1 1 0 0

        This would draw a character on the screen that looks like an 'E'. The
        x_source and y_source tell which registers contain the x and y
        coordinates for the sprite. If writing a pixel to a location causes
        that pixel to be turned off, then VF will be set to 1.

           Bits:  15-12     11-8      7-4       3-0
                  unused    x_source  y_source  num_bytes
        """
        cpu_x_source = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_y_source = (self.cpu_operand & ADDRESS_4) >> 4
        cpu_x_pos = self.cpu_registers['v'][cpu_x_source]
        cpu_y_pos = self.cpu_registers['v'][cpu_y_source]
        cpu_num_bytes = self.cpu_operand & ADDRESS_6
        self.cpu_registers['v'][0xF] = 0

        if self.cpu_mode == MODE_EXTENDED and cpu_num_bytes == 0:
            self.cpu_draw_extended(cpu_x_pos, cpu_y_pos, 16)
        else:
            self.cpu_draw_normal(cpu_x_pos, cpu_y_pos, cpu_num_bytes)

    def cpu_draw_normal(self, cpu_x_pos, cpu_y_pos, cpu_num_bytes):
        """
        Draws a sprite on the screen while in NORMAL mode.
        
        :param x_pos: the X position of the sprite
        :param y_pos: the Y position of the sprite
        :param num_bytes: the number of bytes to draw
        """
        for cpu_y_index in xrange(cpu_num_bytes):

            cpu_color_byte = bin(self.cpu_memory[self.cpu_registers['index'] + cpu_y_index])
            cpu_color_byte = cpu_color_byte[2:].zfill(8)
            cpu_y_coord = cpu_y_pos + cpu_y_index
            cpu_y_coord = cpu_y_coord % self.cpu_screen.screen_height

            for cpu_x_index in xrange(8):

                cpu_x_coord = cpu_x_pos + cpu_x_index
                cpu_x_coord = cpu_x_coord % self.cpu_screen.screen_width

                cpu_color = int(cpu_color_byte[cpu_x_index])
                cpu_current_color = self.cpu_screen.get_screen_pixel(cpu_x_coord, cpu_y_coord)

                if cpu_color == 1 and cpu_current_color == 1:
                    self.cpu_registers['v'][0xF] = self.cpu_registers['v'][0xF] | 1
                    cpu_color = 0

                elif cpu_color == 0 and cpu_current_color == 1:
                    cpu_color = 1

                self.cpu_screen.draw_screen_pixel(cpu_x_coord, cpu_y_coord, cpu_color)

        self.cpu_screen.update_screen()

    def cpu_draw_extended(self, cpu_x_pos, cpu_y_pos, cpu_num_bytes):
        """
        Draws a sprite on the screen while in EXTENDED mode. Sprites in this
        mode are assumed to be 16x16 pixels. This means that two bytes will
        be read from the memory location, and 16 two-byte sequences in total
        will be read.

        :param x_pos: the X position of the sprite
        :param y_pos: the Y position of the sprite
        :param num_bytes: the number of bytes to draw
        """
        for cpu_y_index in xrange(cpu_num_bytes):

            for cpu_x_byte in xrange(2):

                cpu_color_byte = bin(self.cpu_memory[self.cpu_registers['index'] + (cpu_y_index * 2) + cpu_x_byte])
                cpu_color_byte = cpu_color_byte[2:].zfill(8)
                cpu_y_coord = cpu_y_pos + cpu_y_index
                cpu_y_coord = cpu_y_coord % self.cpu_screen.screen_height

                for cpu_x_index in range(8):

                    cpu_x_coord = cpu_x_pos + cpu_x_index + (cpu_x_byte * 8)
                    cpu_x_coord = cpu_x_coord % self.cpu_screen.screen_width

                    cpu_color = int(cpu_color_byte[cpu_x_index])
                    cpu_current_color = self.cpu_screen.get_screen_pixel(cpu_x_coord, cpu_y_coord)

                    if cpu_color == 1 and cpu_current_color == 1:
                        self.cpu_registers['v'][0xF] = 1
                        cpu_color = 0

                    elif cpu_color == 0 and cpu_current_color == 1:
                        cpu_color = 1

                    self.cpu_screen.draw_screen_pixel(cpu_x_coord, cpu_y_coord, cpu_color)

        self.cpu_screen.update_screen()

    def cpu_move_delay_timer_into_reg(self):
        """
        Ft07 - LOAD Vt, DELAY

        Move the value of the delay timer into the target register. The
        register calculation is as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused    target     0         7
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_registers['v'][cpu_target] = self.cpu_timers['delay']

    def cpu_wait_for_keypress(self):
        """
        Ft0A - KEYD Vt

        Stop execution until a key is pressed. Move the value of the key
        pressed into the specified register. The register calculation is
        as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused    target     0         A
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_key_pressed = False
        while not cpu_key_pressed:
            cpu_event = pygame.event.wait()
            if cpu_event.type == pygame.KEYDOWN:
                cpu_keys_pressed = key.get_pressed()
                for cpu_keyval, cpu_lookup_key in KEY_MAPPINGS.items():
                    if cpu_keys_pressed[cpu_lookup_key]:
                        self.cpu_registers['v'][cpu_target] = cpu_keyval
                        cpu_key_pressed = True
                        break

    def cpu_move_reg_into_delay_timer(self):
        """
        Fs15 - LOAD DELAY, Vs

        Move the value stored in the specified source register into the delay
        timer. The register calculation is as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused    source     1         5
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_timers['delay'] = self.cpu_registers['v'][cpu_source]

    def cpu_move_reg_into_sound_timer(self):
        """
        Fs18 - LOAD SOUND, Vs

        Move the value stored in the specified source register into the sound
        timer. The register calculation is as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused    source     1         8
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_timers['sound'] = self.cpu_registers['v'][cpu_source]

    def cpu_load_index_with_reg_sprite(self):
        """
        Fs29 - LOAD I, Vs

        Load the index with the sprite indicated in the source register. All
        sprites are 5 bytes long, so the location of the specified sprite
        is its index multiplied by 5. The register calculation is as
        follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused    source     2         9
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_registers['index'] = self.cpu_registers['v'][cpu_source] * 5

    def cpu_load_index_with_extended_reg_sprite(self):
        """
        Fs30 - LOAD I, Vs

        Load the index with the sprite indicated in the source register. All
        sprites are 10 bytes long, so the location of the specified sprite
        is its index multiplied by 10. The register calculation is as
        follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused    source     2         9
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_registers['index'] = self.cpu_registers['v'][cpu_source] * 10

    def cpu_add_reg_into_index(self):
        """
        Fs1E - ADD  I, Vs

        Add the value of the register into the index register value. The
        register calculation is as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused    source     1         E
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_registers['index'] += self.cpu_registers['v'][cpu_source]

    def cpu_store_bcd_in_memory(self):
        """
        Fs33 - BCD

        Take the value stored in source and place the digits in the following
        locations:

            hundreds   -> self.memory[index]
            tens       -> self.memory[index + 1]
            ones       -> self.memory[index + 2]

        For example, if the value is 123, then the following values will be
        placed at the specified locations:

             1 -> self.memory[index]
             2 -> self.memory[index + 1]
             3 -> self.memory[index + 2]

        The register calculation is as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused    source     3         3
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_bcd_value = '{:03d}'.format(self.cpu_registers['v'][cpu_source])
        self.cpu_memory[self.cpu_registers['index']] = int(cpu_bcd_value[0])
        self.cpu_memory[self.cpu_registers['index'] + 1] = int(cpu_bcd_value[1])
        self.cpu_memory[self.cpu_registers['index'] + 2] = int(cpu_bcd_value[2])

    def cpu_store_regs_in_memory(self):
        """
        Fs55 - STOR [I], Vs

        Store all of the V registers in the memory pointed to by the index
        register. The register calculation is as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused    source     5         5

        The source register contains the number of V registers to store.
        For example, to store all of the V registers, the source register
        would contain the value 'F'.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        for cpu_counter in range(cpu_source + 1):
            self.cpu_memory[self.cpu_registers['index'] + cpu_counter] = \
                    self.cpu_registers['v'][cpu_counter]

    def cpu_read_regs_from_memory(self):
        """
        Fs65 - LOAD Vs, [I]

        Read all of the V registers from the memory pointed to by the index
        register. The register calculation is as follows:

           Bits:  15-12     11-8      7-4       3-0
                  unused    source     6         5

        The source register contains the number of V registers to load. For
        example, to load all of the V registers, the source register would
        contain the value 'F'.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        for cpu_counter in range(cpu_source + 1):
            self.cpu_registers['v'][cpu_counter] = \
                    self.cpu_memory[self.cpu_registers['index'] + cpu_counter]

    def cpu_store_regs_in_rpl(self):
        """
        Fs75 - SRPL Vs

        Stores all or fewer of the V registers in the RPL store.

           Bits:  15-12     11-8      7-4       3-0
                  unused    source     7         5

        The source register contains the number of V registers to store.
        For example, to store all of the V registers, the source register
        would contain the value 'F'.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        for cpu_counter in range(cpu_source + 1):
            self.cpu_registers['rpl'][cpu_counter] = self.cpu_registers['v'][cpu_counter]

    def cpu_read_regs_from_rpl(self):
        """
        Fs85 - LRPL Vs

        Read all or fewer of the V registers from the RPL store.

           Bits:  15-12     11-8      7-4       3-0
                  unused    source     6         5

        The source register contains the number of V registers to load. For
        example, to load all of the V registers, the source register would
        contain the value 'F'.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        for cpu_counter in range(cpu_source + 1):
            self.cpu_registers['v'][cpu_counter] = self.cpu_registers['rpl'][cpu_counter]

    def cpu_reset(self):
        """
        Reset the CPU by blanking out all registers, and reseting the stack
        pointer and program counter to their starting values.
        """
        self.cpu_registers['v'] = [0] * NUM_REGISTERS
        self.cpu_registers['pc'] = PROGRAM_COUNTER_START
        self.cpu_registers['sp'] = STACK_POINTER_START
        self.cpu_registers['index'] = 0
        self.cpu_registers['rpl'] = [0] * NUM_REGISTERS
        self.cpu_timers['delay'] = 0
        self.cpu_timers['sound'] = 0

    def cpu_load_rom(self, filename, cpu_offset=PROGRAM_COUNTER_START):
        """
        Load the ROM indicated by the filename into memory.

        @param filename: the name of the file to load
        @type filename: string

        @param offset: the location in memory at which to load the ROM
        @type offset: integer
        """
        cpu_romdata = open(filename, 'rb').read()
        for cpu_index, cpu_val in enumerate(cpu_romdata):
            self.cpu_memory[cpu_offset + cpu_index] = cpu_val

    def cpu_decrement_timers(self):
        """
        Decrement both the sound and delay timer.
        """
        if self.cpu_timers['delay'] != 0:
            self.cpu_timers['delay'] -= 1

        if self.cpu_timers['sound'] != 0:
            self.cpu_timers['sound'] -= 1
