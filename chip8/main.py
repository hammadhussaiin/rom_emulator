import argparse
import pygame

from cpu import CPU
from screen import Screen

# A simple timer event used for the delay and sound timers
TIMER = pygame.USEREVENT + 1
# The font file to use
FONT_FILE = "FONTS.chip8"
# Delay timer decrement interval (in ms)
DELAY_INTERVAL = 17
EXIT_STATE = 0x00FD


def screen_cpu_connector(args):
    """
    Runs the main emulator loop with the specified arguments.

    :param args: the parsed command-line arguments
    """
    project_screen = Screen(ratio=args.scale)
    project_screen.init_display()
    project_cpu = CPU(project_screen)
    project_cpu.cpu_load_rom(FONT_FILE, 0)
    project_cpu.cpu_load_rom(args.rom)
    pygame.time.set_timer(TIMER, DELAY_INTERVAL)
    running = True

    while running:
        pygame.time.wait(args.op_delay)
        operand = project_cpu.cpu_execute_instruction()

        # Check for events
        for event in pygame.event.get():
            if event.type == TIMER:
                project_cpu.cpu_decrement_timers()
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                keys_pressed = pygame.key.get_pressed()
                if keys_pressed[pygame.K_q]:
                    running = False

        # Check to see if CPU is in exit state
        if operand == EXIT_STATE:
            running = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Starts a simple Chip 8 "
                    )
    parser.add_argument(
        "rom", help="the ROM file to load on startup")
    parser.add_argument(
        "-s", help="the scale factor to apply to the display "
                   "(default is 5)", type=int, default=5, dest="scale")
    parser.add_argument(
        "-d", help="sets the CPU operation to take at least "
                   "the specified number of milliseconds to execute (default is 1)",
        type=int, default=1, dest="op_delay")
    screen_cpu_connector(parser.parse_args())
