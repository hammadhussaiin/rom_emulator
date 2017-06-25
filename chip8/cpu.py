import pygame
from exception import UnknownOpCodeException
from pygame import key
from random import randint
from addresses import *

MAX_MEMORY = 4096

STACK_POINTER_START = 0x52

PROGRAM_COUNTER_START = 0x200

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

NUM_REGISTERS = 0x10

MODE_NORMAL = 'normal'
MODE_EXTENDED = 'extended'


class CPU(object):
    """
    Class to imitate the behavior of a Chip-8 processor
    """
    def __init__(self, screen):
        """
        Class chip-8 constructor it initialize the processor.

        :param screen: the screen object is passed for the chip8 processor to draw on
        """
        self.cpu_timers = {
            'delay': 0,
            'sound': 0,
        }
        self.cpu_registers = {
            'v': [],
            'index': 0,
            'sp': 0,
            'pc': 0,
            'rpl': []
        }
        self.cpu_operation_lookup = {
            0x0: self.cpu_clear_return,
            0x1: self.cpu_jump_to_address,
            0x2: self.cpu_jump_to_subroutine,
            0x3: self.cpu_skip_if_reg_equal_val,
            0x4: self.cpu_skip_if_reg_not_equal_val,
            0x5: self.cpu_skip_if_reg_equal_reg,
            0x6: self.cpu_move_value_to_reg,
            0x7: self.cpu_add_value_to_reg,
            0x8: self.cpu_execute_logical_instruction,
            0x9: self.cpu_skip_if_reg_not_equal_reg,
            0xA: self.cpu_load_index_reg_with_value,
            0xB: self.cpu_jump_to_index_plus_value,
            0xC: self.cpu_generate_random_number,
            0xD: self.cpu_draw_sprite,
            0xE: self.cpu_keyboard_routines,
            0xF: self.cpu_misc_routines,
        }
        self.cpu_logical_operation_lookup = {
            0x0: self.cpu_move_reg_into_reg,
            0x1: self.cpu_logical_or,
            0x2: self.cpu_logical_and,
            0x3: self.cpu_exclusive_or,
            0x4: self.cpu_add_reg_to_reg,
            0x5: self.cpu_subtract_reg_from_reg,
            0x6: self.cpu_right_shift_reg,
            0x7: self.cpu_subtract_reg_from_reg1,
            0xE: self.cpu_left_shift_reg,
        }
        self.cpu_misc_routine_lookup = {
            0x07: self.cpu_move_delay_timer_into_reg,
            0x0A: self.cpu_wait_for_keypress,
            0x15: self.cpu_move_reg_into_delay_timer,
            0x18: self.cpu_move_reg_into_sound_timer,
            0x1E: self.cpu_add_reg_into_index,
            0x29: self.cpu_load_index_with_reg_sprite,
            0x30: self.cpu_load_index_with_extended_reg_sprite,
            0x33: self.cpu_store_bcd_in_memory,
            0x55: self.cpu_store_regs_in_memory,
            0x65: self.cpu_read_regs_from_memory,
            0x75: self.cpu_store_regs_in_rpl,
            0x85: self.cpu_read_regs_from_rpl,
        }
        self.cpu_operand = 0
        self.cpu_mode = MODE_NORMAL
        self.cpu_screen = screen
        self.cpu_memory = bytearray(MAX_MEMORY)
        self.cpu_reset()

    def __str__(self):
        val = 'PC: {:4X}  OP: {:4X}\n'.format(
            self.cpu_registers['pc'] - 2, self.cpu_operand)
        for index in range(0x10):
            val += 'V{:X}: {:2X}\n'.format(index, self.cpu_registers['v'][index])
        val += 'I: {:4X}\n'.format(self.cpu_registers['index'])
        return val

    def cpu_execute_instruction(self, cpu_operator_param=None):
        """
        This method executes the next instruction in the program counter.
        If cpu_operator_param is not passed program counter is incremented by 2.

        :param cpu_operator_param: the operand to execute
        :return: returns executed cpu_operator_param
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
        Logical instruction is executed based upon what the current operand is.
        """
        cpu_operation = self.cpu_operand & ADDRESS_6
        try:
            self.cpu_logical_operation_lookup[cpu_operation]()
        except KeyError:
            raise UnknownOpCodeException(self.cpu_operand)

    def cpu_keyboard_routines(self):
        """
        Keyboard routines are fired based up current operandyth.
        """
        cpu_operation = self.cpu_operand & ADDRESS_2
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8

        cpu_key_to_check = self.cpu_registers['v'][cpu_source]
        cpu_keys_pressed = key.get_pressed()

        if cpu_operation == 0x9E:
            if cpu_keys_pressed[KEY_MAPPINGS[cpu_key_to_check]]:
                self.cpu_registers['pc'] += 2

        if cpu_operation == 0xA1:
            if not cpu_keys_pressed[KEY_MAPPINGS[cpu_key_to_check]]:
                self.cpu_registers['pc'] += 2

    def cpu_misc_routines(self):
        """
        One of the miscellaneous routines is fired.
        """
        cpu_operation = self.cpu_operand & ADDRESS_2
        try:
            self.cpu_misc_routine_lookup[cpu_operation]()
        except KeyError:
            raise UnknownOpCodeException(self.cpu_operand)

    def cpu_clear_return(self):
        """
        Method deciphers the opcodes based cpi_operation deciding if it starts with 0.
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
        This method is for jumping to address
        """
        self.cpu_registers['pc'] = self.cpu_operand & ADDRESS_13

    def cpu_jump_to_subroutine(self):
        """
        This method jumps to subroutine and saves
        current program counter on the stack.
        """
        self.cpu_memory[self.cpu_registers['sp']] = self.cpu_registers['pc'] & ADDRESS_2
        self.cpu_registers['sp'] += 1
        self.cpu_memory[self.cpu_registers['sp']] = (self.cpu_registers['pc'] & ADDRESS_14) >> 8
        self.cpu_registers['sp'] += 1
        self.cpu_registers['pc'] = self.cpu_operand & ADDRESS_13

    def cpu_skip_if_reg_equal_val(self):
        """
        This method skips if the contents in the register are
        equal to constant value. The program counter skips by
        advancing 2 bytes.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        if self.cpu_registers['v'][cpu_source] == (self.cpu_operand & ADDRESS_2):
            self.cpu_registers['pc'] += 2

    def cpu_skip_if_reg_not_equal_val(self):
        """
        This method skips if the contents in the register are not
        equal to constant value. The program counter skips by
        advancing 2 bytes.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        if self.cpu_registers['v'][cpu_source] != (self.cpu_operand & ADDRESS_2):
            self.cpu_registers['pc'] += 2

    def cpu_skip_if_reg_equal_reg(self):
        """
        This method skips if the contents in the register are
        equal to the target register. The program counter skips by
        advancing 2 bytes.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_target = (self.cpu_operand & ADDRESS_4) >> 4
        if self.cpu_registers['v'][cpu_source] == self.cpu_registers['v'][cpu_target]:
            self.cpu_registers['pc'] += 2

    def cpu_move_value_to_reg(self):
        """
        This method updates the specified register with the constant value.
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_registers['v'][cpu_target] = self.cpu_operand & ADDRESS_2

    def cpu_add_value_to_reg(self):
        """
        This method adds the constant value in the specified register
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        temp = self.cpu_registers['v'][cpu_target] + (self.cpu_operand & ADDRESS_2)
        self.cpu_registers['v'][cpu_target] = temp if temp < 256 else temp - 256

    def cpu_move_reg_into_reg(self):
        """
        This method updates target register with the value in the
        source register.
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_source = (self.cpu_operand & ADDRESS_4) >> 4
        self.cpu_registers['v'][cpu_target] = self.cpu_registers['v'][cpu_source]

    def cpu_logical_or(self):
        """
        This method updates the target register with the logical OR of source register
        and target register
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_source = (self.cpu_operand & ADDRESS_4) >> 4
        self.cpu_registers['v'][cpu_target] |= self.cpu_registers['v'][cpu_source]

    def cpu_logical_and(self):
        """
        This method updates the target register with the logical AND of source register
        and target register
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_source = (self.cpu_operand & ADDRESS_4) >> 4
        self.cpu_registers['v'][cpu_target] &= self.cpu_registers['v'][cpu_source]

    def cpu_exclusive_or(self):
        """
        This method updates the target register with the logical XOR of source register
        and target register
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_source = (self.cpu_operand & ADDRESS_4) >> 4
        self.cpu_registers['v'][cpu_target] ^= self.cpu_registers['v'][cpu_source]

    def cpu_add_reg_to_reg(self):
        """
        This method adds value of source and target register
        and stores it in the target register. If carry is generated
        the carry flag is set in the VF register.
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
        This method subtracts value of target from the source register
        and stores it in the target register. If borrow is NOT
        generated the carry flag is set in the VF register.
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
        This methods performs shift right on the specified register. 0th Bit
        will be stored in the vf register
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_bit_zero = self.cpu_registers['v'][cpu_source] & 0x1
        self.cpu_registers['v'][cpu_source] >>= 1
        self.cpu_registers['v'][0xF] = cpu_bit_zero

    def cpu_subtract_reg_from_reg1(self):
        """
        This method subtracts value of source from the target register
        and stores it in the target register. If borrow is NOT
        generated the carry flag is set in the VF register.
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
        This methods performs shift left on the specified register. 7th Bit
        will be stored in the vf register
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_bit_seven = (self.cpu_registers['v'][cpu_source] & 0x80) >> 8
        self.cpu_registers['v'][cpu_source] <<= 1
        self.cpu_registers['v'][0xF] = cpu_bit_seven

    def cpu_skip_if_reg_not_equal_reg(self):
        """
        This method skips if the source register is
        equal to the target register. The program counter skips by
        advancing 2 bytes.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_target = (self.cpu_operand & ADDRESS_4) >> 4
        if self.cpu_registers['v'][cpu_source] != self.cpu_registers['v'][cpu_target]:
            self.cpu_registers['pc'] += 2

    def cpu_load_index_reg_with_value(self):
        """
        This method updates the index register with a constant value.
        """
        self.cpu_registers['index'] = self.cpu_operand & ADDRESS_13

    def cpu_jump_to_index_plus_value(self):
        """
        This method updates the program counter with memory value at
        index register + operand
        """
        self.cpu_registers['pc'] = self.cpu_registers['index'] + (self.cpu_operand & ADDRESS_13)

    def cpu_generate_random_number(self):
        """
        This method generates a random number between 0 and 255 and then AND(s)
        it with the constant value passed in the operand. Then it stores the
        result in the target register.
        """
        cpu_value = self.cpu_operand & ADDRESS_2
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_registers['v'][cpu_target] = cpu_value & randint(0, 255)

    def cpu_draw_sprite(self):
        """
        This method draws a sprite pointed to in the index register at the
        x and y coordinates.
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
        This method draws a sprite while in the NORMAL mode.

        :param cpu_x_pos: x coordinate of the sprite
        :param cpu_y_pos: y coordinate of the sprite
        :param cpu_num_bytes: the total number of bytes to draw.
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
                    self.cpu_registers['v'][0xF] |= 1
                    cpu_color = 0

                elif cpu_color == 0 and cpu_current_color == 1:
                    cpu_color = 1

                self.cpu_screen.draw_screen_pixel(cpu_x_coord, cpu_y_coord, cpu_color)

        self.cpu_screen.update_screen()

    def cpu_draw_extended(self, cpu_x_pos, cpu_y_pos, cpu_num_bytes):
        """
        This method draws a sprite while in the EXTENDED mode.

        :param cpu_x_pos: x coordinate of the sprite
        :param cpu_y_pos: y coordinate of the sprite
        :param cpu_num_bytes: the total number of bytes to draw.
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
        This method updates the target register with the value of the
        delay timer
        """
        cpu_target = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_registers['v'][cpu_target] = self.cpu_timers['delay']

    def cpu_wait_for_keypress(self):
        """
        This method executes until a key is pressed. Then updates the
        specified register with the value of the key.
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
        This method updates the delay timer with the value in the source
        register.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_timers['delay'] = self.cpu_registers['v'][cpu_source]

    def cpu_move_reg_into_sound_timer(self):
        """
        This method updates the sound timer with the value in the source
        register.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_timers['sound'] = self.cpu_registers['v'][cpu_source]

    def cpu_load_index_with_reg_sprite(self):
        """
        This method updates the index register with the sprite in
        the source register.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_registers['index'] = self.cpu_registers['v'][cpu_source] * 5

    def cpu_load_index_with_extended_reg_sprite(self):
        """
        This method updates the index register with the sprite in
        the source register in EXTENDED mode.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_registers['index'] = self.cpu_registers['v'][cpu_source] * 10

    def cpu_add_reg_into_index(self):
        """
        This method updates the value of index register with the
        sum of the values in the index and source registers.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        self.cpu_registers['index'] += self.cpu_registers['v'][cpu_source]

    def cpu_store_bcd_in_memory(self):
        """
        This method places numerals in memory at indexes such that memory at
        index 0 gets hundreds, memory at index 1 gets tens, memory at
        index 2 gets ones.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        cpu_bcd_value = '{:03d}'.format(self.cpu_registers['v'][cpu_source])
        self.cpu_memory[self.cpu_registers['index']] = int(cpu_bcd_value[0])
        self.cpu_memory[self.cpu_registers['index'] + 1] = int(cpu_bcd_value[1])
        self.cpu_memory[self.cpu_registers['index'] + 2] = int(cpu_bcd_value[2])

    def cpu_store_regs_in_memory(self):
        """
        This method stores the value of all the V registers in the memory
        pointed to by the index register
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        for cpu_counter in range(cpu_source + 1):
            self.cpu_memory[self.cpu_registers['index'] + cpu_counter] = \
                    self.cpu_registers['v'][cpu_counter]

    def cpu_read_regs_from_memory(self):
        """
        This method reads all of the V registers from the memory pointed to by the index
        register.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        for cpu_counter in range(cpu_source + 1):
            self.cpu_registers['v'][cpu_counter] = \
                    self.cpu_memory[self.cpu_registers['index'] + cpu_counter]

    def cpu_store_regs_in_rpl(self):
        """
        This method stores the V registers in the RPL store.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        for cpu_counter in range(cpu_source + 1):
            self.cpu_registers['rpl'][cpu_counter] = self.cpu_registers['v'][cpu_counter]

    def cpu_read_regs_from_rpl(self):
        """
        This method reads the V registers in the RPL store.
        """
        cpu_source = (self.cpu_operand & ADDRESS_3) >> 8
        for cpu_counter in range(cpu_source + 1):
            self.cpu_registers['v'][cpu_counter] = self.cpu_registers['rpl'][cpu_counter]

    def cpu_reset(self):
        """
        This method completely resets the CPU. It flashes all registers and
        sets the stack pointer and program counter to their initial values.
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
        This method loads the ROM from filename to memory

        @param filename: the name of the file to load
        @param cpu_offset: the location in memory at which to load the ROM
        """
        cpu_romdata = open(filename, 'rb').read()
        for cpu_index, cpu_val in enumerate(cpu_romdata):
            self.cpu_memory[cpu_offset + cpu_index] = cpu_val

    def cpu_decrement_timers(self):
        """
        This method decrements both delay and sound timers by one.
        """
        if self.cpu_timers['delay'] != 0:
            self.cpu_timers['delay'] -= 1

        if self.cpu_timers['sound'] != 0:
            self.cpu_timers['sound'] -= 1
