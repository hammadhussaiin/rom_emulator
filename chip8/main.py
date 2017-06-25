import argparse
import pygame

from cpu import CPU
from screen import Screen

TIMER = pygame.USEREVENT + 1
FONT_FILE = "FONTS.chip8"
DELAY_INTERVAL = 17
EXIT_STATE = 0x00FD


def screen_cpu_connector(args):
    """
    This method runs the main emulator loop with the arguments.

    :param args: the parsed command-line arguments passed
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

        for event in pygame.event.get():
            if event.type == TIMER:
                project_cpu.cpu_decrement_timers()
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                keys_pressed = pygame.key.get_pressed()
                if keys_pressed[pygame.K_q]:
                    running = False

        if operand == EXIT_STATE:
            running = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Initiates Chip-8 Processor"
                    )
    parser.add_argument(
        "rom", help="The input ROM file")
    parser.add_argument(
        "-s", help="The scaling factor to be applied to the screen"
                   "(default is 5)", type=int, default=5, dest="scale")
    parser.add_argument(
        "-d", help="Sets the CPU to take exactly"
                   "the specified delay in number of milliseconds to execute (default is 1)",
        type=int, default=1, dest="op_delay")
    screen_cpu_connector(parser.parse_args())
